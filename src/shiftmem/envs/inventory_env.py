"""Deterministic-seed lost-sales inventory environment."""

from typing import Any, Mapping

import numpy as np

from .demand_models import DemandModel, NegativeBinomialDemand, PoissonDemand
from .shifts import Scenario
from .supply_models import SingleSupplier


class InventoryEnv:
    """A single-item lost-sales environment with delayed replenishment."""

    def __init__(
        self,
        scenario: Scenario,
        demand_model: DemandModel | None = None,
        supplier: SingleSupplier | None = None,
    ) -> None:
        self.scenario = scenario
        self.demand_model = demand_model or (
            PoissonDemand()
            if scenario.demand_model == "poisson"
            else NegativeBinomialDemand()
        )
        self.supplier = supplier or SingleSupplier()
        self._demand_rng = np.random.default_rng()
        self._supply_rng = np.random.default_rng()
        self._terminated = True
        self.records: list[dict[str, Any]] = []

    def reset(self, seed: int | None = None) -> tuple[dict[str, Any], dict[str, str]]:
        demand_seed, supply_seed = np.random.SeedSequence(seed).spawn(2)
        self._demand_rng = np.random.default_rng(demand_seed)
        self._supply_rng = np.random.default_rng(supply_seed)
        self.day = 0
        self.inventory = self.scenario.initial_inventory
        self.pending_orders: dict[int, list[tuple[int, Any]]] = {}
        self.last_demand = 0
        self.last_sales = 0
        self.records = []
        self._terminated = False
        return self._observation(), {"scenario": self.scenario.name}

    def step(
        self, action: Mapping[str, Any]
    ) -> tuple[dict[str, int], float, bool, bool, dict[str, Any]]:
        if self._terminated:
            raise RuntimeError("reset must be called before stepping a finished episode")
        quantity = self._validate_action(action)
        parameters = self.scenario.parameters_at(self.day)

        starting_inventory = self.inventory
        arrivals = sum(
            self.supplier.arrival_quantity(
                quantity, self._supply_rng, supply_parameters
            )
            for quantity, supply_parameters in self.pending_orders.pop(self.day, [])
        )
        self.inventory += arrivals
        demand = self.demand_model.sample(self._demand_rng, parameters.demand)
        sales = min(self.inventory, demand)
        lost_sales = demand - sales
        self.inventory -= sales

        if quantity:
            due_day = self.day + parameters.supply.lead_time
            self.pending_orders.setdefault(due_day, []).append(
                (quantity, parameters.supply)
            )

        costs = self.scenario.costs
        purchase_cost = quantity * costs.purchase
        holding_cost = self.inventory * costs.holding
        stockout_cost = lost_sales * costs.stockout
        ordering_cost = costs.fixed_order if quantity > 0 else 0.0
        total_cost = purchase_cost + holding_cost + stockout_cost + ordering_cost

        record: dict[str, Any] = {
            "day": self.day,
            "quoted_lead_time": parameters.supply.lead_time,
            "starting_inventory": starting_inventory,
            "arrivals": arrivals,
            "demand": demand,
            "sales": sales,
            "lost_sales": lost_sales,
            "ending_inventory": self.inventory,
            "order_quantity": quantity,
            "pipeline_inventory": self._pipeline_inventory(),
            "purchase_cost": purchase_cost,
            "holding_cost": holding_cost,
            "stockout_cost": stockout_cost,
            "ordering_cost": ordering_cost,
            "total_cost": total_cost,
        }
        self.records.append(record)
        self.last_demand = demand
        self.last_sales = sales
        self.day += 1
        self._terminated = self.day >= self.scenario.episode_length
        return self._observation(), -float(total_cost), self._terminated, False, record.copy()

    def oracle_context(self) -> dict[str, float | int | str]:
        day = min(self.day, self.scenario.episode_length - 1)
        parameters = self.scenario.parameters_at(day)
        return {
            "demand_model": self.scenario.demand_model,
            "demand_mean": parameters.demand.mean,
            "dispersion": parameters.demand.dispersion,
            "lead_time": parameters.supply.lead_time,
            "fill_rate": parameters.supply.fill_rate,
        }

    def _observation(self) -> dict[str, Any]:
        public_history_keys = (
            "day",
            "demand",
            "sales",
            "lost_sales",
            "ending_inventory",
            "order_quantity",
            "arrivals",
            "total_cost",
        )
        parameter_day = min(self.day, self.scenario.episode_length - 1)
        costs = self.scenario.costs
        return {
            "day": self.day,
            "inventory": self.inventory,
            "pipeline_inventory": self._pipeline_inventory(),
            "pipeline_orders": self._pipeline_orders(),
            "quoted_lead_time": self.scenario.parameters_at(
                parameter_day
            ).supply.lead_time,
            "last_demand": self.last_demand,
            "last_sales": self.last_sales,
            "costs": {
                "purchase": costs.purchase,
                "holding": costs.holding,
                "stockout": costs.stockout,
                "fixed_order": costs.fixed_order,
            },
            "recent_history": [
                {key: record[key] for key in public_history_keys}
                for record in self.records[-14:]
            ],
        }

    def _pipeline_orders(self) -> list[dict[str, int]]:
        return [
            {"due_day": due_day, "quantity": quantity}
            for due_day in sorted(self.pending_orders)
            for quantity, _ in self.pending_orders[due_day]
        ]

    def _pipeline_inventory(self) -> int:
        return sum(
            quantity
            for orders in self.pending_orders.values()
            for quantity, _ in orders
        )

    @staticmethod
    def _validate_action(action: Mapping[str, Any]) -> int:
        if set(action) != {"order_quantity", "supplier_id"}:
            raise ValueError("action requires order_quantity and supplier_id")
        if action["supplier_id"] != "standard":
            raise ValueError("unsupported supplier_id")
        quantity = action["order_quantity"]
        if not isinstance(quantity, (int, np.integer)):
            raise TypeError("order_quantity must be an integer")
        if quantity < 0:
            raise ValueError("order_quantity must be non-negative")
        return int(quantity)
