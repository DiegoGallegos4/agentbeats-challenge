import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
import pandas as pd
from pydantic import BaseModel, ValidationError
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, Part, TextPart, DataPart
from a2a.utils import get_message_text, new_agent_text_message

from messenger import Messenger
from agentbeats.portfolio.tools import data_manager as portfolio_data_manager


class EvalRequest(BaseModel):
    """Request format sent by the AgentBeats platform to green agents."""
    participants: dict[str, str]  # role -> agent URL
    config: dict[str, Any]


class Agent:
    required_roles: list[str] = ["agent"]
    required_config_keys: list[str] = ["date", "pnl_date", "tickers"]

    def __init__(self):
        self.messenger = Messenger()
        # Initialize other state here
        self._log_requests = os.environ.get("AGENTBEATS_LOG_MESSAGES") == "1"
        self._repo_root = Path(__file__).resolve().parents[2]

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

    def _resolve_path(self, path_str: str) -> Path:
        path = Path(path_str).expanduser()
        if not path.is_absolute():
            path = self._repo_root / path
        return path

    def _load_jsonl(self, path: Path) -> list[dict[str, Any]]:
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        return rows

    def _parse_yes_no(self, value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            cleaned = value.strip().lower()
            if cleaned in {"yes", "y", "true", "1"}:
                return True
            if cleaned in {"no", "n", "false", "0"}:
                return False
        return None

    def _parse_float(self, value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace("$", "").replace(",", "").strip()
            match = re.search(r"-?\d+(\.\d+)?", cleaned)
            if match:
                return float(match.group(0))
        return None

    def _parse_multi_choice(self, value: Any) -> set[str]:
        if value is None:
            return set()
        if isinstance(value, list):
            return {str(item).strip().upper() for item in value if str(item).strip()}
        if isinstance(value, str):
            parts = re.split(r"[,\s]+", value.strip())
            return {part.upper() for part in parts if part}
        return {str(value).strip().upper()}

    def _market_file_for_date(self, ticker: str, target_date: str) -> Path | None:
        data_root = Path(portfolio_data_manager.BASE_DIR)
        try:
            target = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            return None

        candidates = []
        for path in data_root.glob(f"*/market/{ticker}.csv"):
            try:
                folder_date = datetime.strptime(path.parent.parent.name, "%Y-%m-%d").date()
            except ValueError:
                continue
            candidates.append((folder_date, path))

        if not candidates:
            return None

        on_or_after = [item for item in candidates if item[0] >= target]
        if on_or_after:
            on_or_after.sort(key=lambda item: item[0])
            return on_or_after[0][1]

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _load_market_series(self, ticker: str, target_date: str) -> tuple[list[dict[str, Any]], int | None]:
        csv_path = self._market_file_for_date(ticker, target_date)
        if not csv_path:
            return [], None
        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        target_ts = pd.to_datetime(target_date, errors="coerce")
        if pd.isna(target_ts):
            return [], None
        matches = df.index[df["date"] == target_ts]
        if matches.empty:
            return [], None
        return df.to_dict("records"), int(matches[0])

    def _score_numeric(self, actual: float, predicted: float, history: list[float]) -> float:
        if not history:
            return 0.0
        sigma = float(pd.Series(history).std(ddof=0))
        if sigma == 0.0:
            return 1.0 if abs(actual - predicted) < 1e-9 else 0.0
        score = 1.0 - ((actual - predicted) / sigma) ** 2
        return max(0.0, score)

    def _evaluate_task(self, task: dict[str, Any], prediction: Any) -> dict[str, Any]:
        level = int(task.get("level", 0))
        level_name = task.get("level_name", "Unknown")
        ticker = task.get("ticker")
        end_time = task.get("end_time")
        target_date = None
        if end_time:
            target_date = str(pd.to_datetime(end_time, errors="coerce").date())

        if level == 1:
            parsed = self._parse_yes_no(prediction)
            if parsed is None or not ticker or not target_date:
                return {"score": 0.0, "ground_truth": None, "level": level, "level_name": level_name}
            rows, idx = self._load_market_series(ticker, target_date)
            if idx is None or idx == 0:
                return {"score": 0.0, "ground_truth": None, "level": level, "level_name": level_name}
            prev_close = float(rows[idx - 1]["close"])
            close = float(rows[idx]["close"])
            gt = close > prev_close
            return {
                "score": 1.0 if parsed == gt else 0.0,
                "ground_truth": gt,
                "level": level,
                "level_name": level_name,
            }

        if level == 2:
            tickers = task.get("tickers") or []
            tickers = [str(t).upper() for t in tickers]
            if not tickers or not target_date:
                return {"score": 0.0, "ground_truth": [], "level": level, "level_name": level_name}
            gt_set = set()
            for symbol in tickers:
                rows, idx = self._load_market_series(symbol, target_date)
                if idx is None or idx == 0:
                    continue
                prev_close = float(rows[idx - 1]["close"])
                close = float(rows[idx]["close"])
                if close > prev_close:
                    gt_set.add(symbol)
            pred_set = self._parse_multi_choice(prediction)
            overlap = gt_set & pred_set
            precision = len(overlap) / len(pred_set) if pred_set else 0.0
            recall = len(overlap) / len(gt_set) if gt_set else 0.0
            score = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
            return {
                "score": score,
                "ground_truth": sorted(gt_set),
                "level": level,
                "level_name": level_name,
            }

        if level in {3, 4}:
            predicted = self._parse_float(prediction)
            if predicted is None or not ticker or not target_date:
                return {"score": 0.0, "ground_truth": None, "level": level, "level_name": level_name}
            rows, idx = self._load_market_series(ticker, target_date)
            if idx is None:
                return {"score": 0.0, "ground_truth": None, "level": level, "level_name": level_name}
            history_slice = rows[max(0, idx - 6) : idx + 1]
            if level == 3:
                actual = float(rows[idx]["close"])
                history = [float(row["close"]) for row in history_slice]
            else:
                actual = float(rows[idx]["high"]) - float(rows[idx]["low"])
                history = [float(row["high"]) - float(row["low"]) for row in history_slice]
            score = self._score_numeric(actual, predicted, history)
            return {
                "score": score,
                "ground_truth": actual,
                "level": level,
                "level_name": level_name,
            }

        return {"score": 0.0, "ground_truth": None, "level": level, "level_name": level_name}

    def _evaluate_benchmark(
        self,
        benchmark_path: Path,
        predictions_path: Path | None,
        predictions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tasks = self._load_jsonl(benchmark_path)
        predictions = predictions or {}
        if predictions_path and predictions_path.exists():
            for row in self._load_jsonl(predictions_path):
                pred_id = row.get("id")
                if pred_id:
                    predictions[pred_id] = row.get("answer") or row.get("prediction")

        scored = []
        per_level = {}
        for task in tasks:
            task_id = task.get("id")
            prediction = predictions.get(task_id)
            result = self._evaluate_task(task, prediction)
            score = result["score"]
            level = result["level"]
            per_level.setdefault(level, []).append(score)
            scored.append(
                {
                    "id": task_id,
                    "level": level,
                    "level_name": result["level_name"],
                    "ticker": task.get("ticker"),
                    "score": score,
                    "ground_truth": result["ground_truth"],
                    "prediction": prediction,
                }
            )

        summaries = {}
        for level, scores in per_level.items():
            summaries[str(level)] = {
                "count": len(scores),
                "avg_score": sum(scores) / len(scores) if scores else 0.0,
            }

        return {
            "task_count": len(scored),
            "per_level": summaries,
            "tasks": scored,
        }

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
            if weight > 0:
                position = "long"
            elif weight < 0:
                position = "short"
            else:
                position = "flat"
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
                        "position": position,
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
                    "position": position,
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
        config = request.config or {}
        if "benchmark_path" not in config:
            participant_roles = {role for role, url in request.participants.items() if url}
            missing_roles = set(self.required_roles) - participant_roles
            if missing_roles:
                return False, f"Missing roles: {missing_roles}"

            missing_config_keys = set(self.required_config_keys) - set(config.keys())
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
        if self._log_requests:
            print(f"[GREEN IN] {input_text}")

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
        benchmark_path = config.get("benchmark_path")
        if benchmark_path:
            benchmark_path = self._resolve_path(benchmark_path)
            if not benchmark_path.exists():
                await updater.reject(new_agent_text_message(f"Missing benchmark_path: {benchmark_path}"))
                return
            predictions_path = config.get("predictions_path")
            predictions_path = self._resolve_path(predictions_path) if predictions_path else None

            await updater.update_status(
                TaskState.working,
                new_agent_text_message("Scoring FinanceX benchmark tasks..."),
            )
            predictions = None
            if predictions_path is None:
                tasks = self._load_jsonl(benchmark_path)
                agent_url = request.participants.get("agent", "")
                if not agent_url:
                    await updater.reject(new_agent_text_message("Missing purple agent URL for predictions."))
                    return
                purple_payload = json.dumps({
                    "participants": {},
                    "config": {
                        "tasks": tasks,
                    },
                })
                response = await self.messenger.talk_to_agent(
                    message=purple_payload,
                    url=str(agent_url),
                    new_conversation=True,
                )
                try:
                    payload = self._extract_payload(response)
                except Exception as e:
                    await updater.reject(new_agent_text_message(f"Failed to parse purple response: {e}"))
                    return
                predictions = {
                    row.get("id"): row.get("prediction")
                    for row in payload.get("predictions", [])
                    if row.get("id")
                }

            benchmark_result = self._evaluate_benchmark(
                benchmark_path,
                predictions_path,
                predictions=predictions,
            )
            summary_lines = ["FinanceX Task Scoring Results"]
            for level, metrics in benchmark_result["per_level"].items():
                summary_lines.append(
                    f"Level {level}: {metrics['count']} tasks, avg score {metrics['avg_score']:.4f}"
                )
            summary_text = "\n".join(summary_lines)

            await updater.add_artifact(
                parts=[
                    Part(root=TextPart(text=summary_text)),
                    Part(root=DataPart(data=benchmark_result)),
                ],
                name="Result",
            )
            return
        date = config.get("date")
        pnl_date = config.get("pnl_date")
        if not date or not pnl_date:
            await updater.reject(new_agent_text_message("Missing date or pnl_date."))
            return

        tickers = config.get("tickers")
        download = bool(config.get("download", True))
        if download:
            if tickers is None or tickers == "subset":
                tickers_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
            elif isinstance(tickers, str):
                tickers_list = [t.strip() for t in tickers.split(",") if t.strip()]
            elif isinstance(tickers, list):
                tickers_list = tickers
            else:
                tickers_list = [str(tickers)]
            try:
                portfolio_data_manager.download_all_data(tickers_list, date)
            except Exception as exc:
                print(f"Warning: download failed for {date}: {exc}")
            if pnl_date != date:
                try:
                    portfolio_data_manager.download_all_data(tickers_list, pnl_date)
                except Exception as exc:
                    print(f"Warning: download failed for {pnl_date}: {exc}")

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
