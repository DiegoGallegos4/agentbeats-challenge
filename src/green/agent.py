import json
from typing import Any
from pydantic import BaseModel, HttpUrl, ValidationError
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, Part, TextPart, DataPart
from a2a.utils import get_message_text, new_agent_text_message

from messenger import Messenger
from agentbeats.portfolio.tools import data_manager as portfolio_data_manager


class EvalRequest(BaseModel):
    """Request format sent by the AgentBeats platform to green agents."""
    participants: dict[str, HttpUrl] # role -> agent URL
    config: dict[str, Any]


class Agent:
    required_roles: list[str] = ["agent"]
    required_config_keys: list[str] = ["date", "pnl_date", "tickers"]

    def __init__(self):
        self.messenger = Messenger()
        # Initialize other state here

    def _extract_payload(self, response: str) -> dict[str, Any]:
        start = response.find("{")
        end = response.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON payload found in purple agent response.")
        payload = response[start : end + 1]
        return json.loads(payload)

    def _get_price(self, ticker: str, target_date: str) -> float | None:
        data = portfolio_data_manager.read_local_market_data(ticker, target_date)
        if not data:
            return None
        price_map = {row["date"]: row["close"] for row in data}
        return price_map.get(target_date)

    def _calculate_pnl(self, weights: list[dict[str, Any]], date: str, pnl_date: str) -> dict[str, Any]:
        rows = []
        missing = 0
        total = 0.0
        pnl_values = []
        returns = []
        gross_exposure = 0.0
        net_exposure = 0.0
        for row in weights:
            ticker = row.get("ticker")
            weight = float(row.get("weight", 0.0))
            gross_exposure += abs(weight)
            net_exposure += weight
            price_prev = self._get_price(ticker, date) if ticker else None
            price_curr = self._get_price(ticker, pnl_date) if ticker else None

            if price_prev is None or price_curr is None:
                missing += 1
                rows.append(
                    {
                        "ticker": ticker,
                        "weight": weight,
                        "return": 0.0,
                        "pnl": 0.0,
                        "price_prev": price_prev,
                        "price_curr": price_curr,
                        "note": "missing price",
                    }
                )
                continue

            ret = (price_curr - price_prev) / price_prev
            pnl = weight * ret
            total += pnl
            pnl_values.append(pnl)
            returns.append(ret)
            rows.append(
                {
                    "ticker": ticker,
                    "weight": weight,
                    "return": ret,
                    "pnl": pnl,
                    "price_prev": price_prev,
                    "price_curr": price_curr,
                }
            )

        hit_rate = (
            sum(1 for pnl in pnl_values if pnl > 0) / len(pnl_values)
            if pnl_values
            else 0.0
        )
        avg_return = sum(returns) / len(returns) if returns else 0.0
        mean_pnl = total / len(pnl_values) if pnl_values else 0.0
        if len(pnl_values) > 1:
            pnl_var = sum((p - mean_pnl) ** 2 for p in pnl_values) / len(pnl_values)
            pnl_std = pnl_var ** 0.5
        else:
            pnl_std = 0.0
        sharpe = mean_pnl / pnl_std if pnl_std else 0.0

        return {
            "total_pnl": total,
            "avg_return": avg_return,
            "hit_rate": hit_rate,
            "gross_exposure": gross_exposure,
            "net_exposure": net_exposure,
            "sharpe": sharpe,
            "missing_prices": missing,
            "rows": rows,
        }

    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        missing_roles = set(self.required_roles) - set(request.participants.keys())
        if missing_roles:
            return False, f"Missing roles: {missing_roles}"

        missing_config_keys = set(self.required_config_keys) - set(request.config.keys())
        if missing_config_keys:
            return False, f"Missing config keys: {missing_config_keys}"

        # Add additional request validation here

        return True, "ok"

    async def run(self, message: Message, updater: TaskUpdater) -> None:
        """Implement your agent logic here.

        Args:
            message: The incoming message
            updater: Report progress (update_status) and results (add_artifact)

        Use self.messenger.talk_to_agent(message, url) to call other agents.
        """
        input_text = get_message_text(message)

        try:
            request: EvalRequest = EvalRequest.model_validate_json(input_text)
            ok, msg = self.validate_request(request)
            if not ok:
                await updater.reject(new_agent_text_message(msg))
                return
        except ValidationError as e:
            await updater.reject(new_agent_text_message(f"Invalid request: {e}"))
            return

        config = request.config or {}
        date = config.get("date")
        pnl_date = config.get("pnl_date")
        if not date or not pnl_date:
            await updater.reject(new_agent_text_message("Missing date or pnl_date."))
            return

        tickers = config.get("tickers")

        await updater.update_status(
            TaskState.working,
            new_agent_text_message("Requesting portfolio weights from purple agent..."),
        )

        purple_payload = json.dumps({
            "participants": {},
            "config": {
                "date": date,
                "tickers": tickers,
            },
        })

        agent_url = str(request.participants["agent"])
        response = await self.messenger.talk_to_agent(
            message=purple_payload,
            url=agent_url,
            new_conversation=True,
        )

        try:
            payload = self._extract_payload(response)
        except Exception as e:
            await updater.reject(new_agent_text_message(f"Failed to parse purple response: {e}"))
            return

        weights = payload.get("weights", [])
        if not weights:
            await updater.reject(new_agent_text_message("Purple agent returned no weights."))
            return

        await updater.update_status(
            TaskState.working,
            new_agent_text_message("Computing portfolio PnL..."),
        )

        pnl_result = self._calculate_pnl(weights, date, pnl_date)
        total_pnl = pnl_result["total_pnl"]
        missing = pnl_result["missing_prices"]
        avg_return = pnl_result["avg_return"]
        hit_rate = pnl_result["hit_rate"]
        gross_exposure = pnl_result["gross_exposure"]
        net_exposure = pnl_result["net_exposure"]
        sharpe = pnl_result["sharpe"]

        summary = (
            "Portfolio Evaluation Results\n"
            f"Date: {date} -> {pnl_date}\n"
            f"Tickers: {len(weights)}\n"
            f"Missing Prices: {missing}\n"
            f"Total PnL: {total_pnl:.6f}\n"
            f"Avg Return: {avg_return:.6f}\n"
            f"Hit Rate: {hit_rate:.2%}\n"
            f"Gross Exposure: {gross_exposure:.4f}\n"
            f"Net Exposure: {net_exposure:.4f}\n"
            f"Sharpe (PnL): {sharpe:.4f}\n"
        )

        await updater.add_artifact(
            parts=[
                Part(root=TextPart(text=summary)),
                Part(root=DataPart(data={
                    "date": date,
                    "pnl_date": pnl_date,
                    "total_pnl": total_pnl,
                    "avg_return": avg_return,
                    "hit_rate": hit_rate,
                    "gross_exposure": gross_exposure,
                    "net_exposure": net_exposure,
                    "sharpe": sharpe,
                    "missing_prices": missing,
                    "rows": pnl_result["rows"],
                })),
            ],
            name="Result",
        )
