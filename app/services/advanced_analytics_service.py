import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
import io
import base64
import json

from ..config import settings
from ..database import db
from .cache_service import cache_service

logger = logging.getLogger(__name__)

class AdvancedAnalyticsService:
    def __init__(self):
        self.initialized = False
        self.cache_ttl = settings.analytics_cache_ttl

    async def initialize(self):
        try:
            self.initialized = True
            logger.info("Advanced analytics service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize advanced analytics service: {e}")

    async def get_financial_forecast(self, days_ahead: int = 30) -> Dict:
        """Forecast revenue for the next N days using linear regression"""
        cache_key = f"financial_forecast_{days_ahead}"
        cached = await cache_service.get(cache_key)
        if cached:
            return {"success": True, "forecast": cached, "cached": True}
        try:
            # Fetch payment data
            result = await db.execute_query(
                "payments",
                "select",
                select_fields=["payment_date", "amount"],
                order_by="payment_date ASC"
            )
            if not result["success"] or not result["data"]:
                return {"success": False, "error": "No payment data available"}
            df = pd.DataFrame(result["data"])
            df["payment_date"] = pd.to_datetime(df["payment_date"])
            df = df.groupby(df["payment_date"].dt.date)["amount"].sum().reset_index()
            df["ordinal_date"] = pd.to_datetime(df["payment_date"]).map(datetime.toordinal)
            X = df[["ordinal_date"]].values
            y = df["amount"].values
            model = LinearRegression()
            model.fit(X, y)
            last_date = df["payment_date"].max()
            forecast_dates = [last_date + timedelta(days=i) for i in range(1, days_ahead + 1)]
            forecast_ordinals = np.array([d.toordinal() for d in forecast_dates]).reshape(-1, 1)
            forecast_amounts = model.predict(forecast_ordinals)
            forecast = [{"date": str(d), "predicted_amount": float(a)} for d, a in zip(forecast_dates, forecast_amounts)]
            await cache_service.set(cache_key, forecast, self.cache_ttl)
            return {"success": True, "forecast": forecast, "cached": False}
        except Exception as e:
            logger.error(f"Failed to generate financial forecast: {e}")
            return {"success": False, "error": str(e)}

    async def get_payment_trends(self, months: int = 6) -> Dict:
        """Analyze payment trends for the last N months"""
        cache_key = f"payment_trends_{months}"
        cached = await cache_service.get(cache_key)
        if cached:
            return {"success": True, "trends": cached, "cached": True}
        try:
            result = await db.execute_query(
                "payments",
                "select",
                select_fields=["payment_date", "amount"],
                order_by="payment_date ASC"
            )
            if not result["success"] or not result["data"]:
                return {"success": False, "error": "No payment data available"}
            df = pd.DataFrame(result["data"])
            df["payment_date"] = pd.to_datetime(df["payment_date"])
            cutoff = datetime.now() - timedelta(days=months * 30)
            df = df[df["payment_date"] >= cutoff]
            df["month"] = df["payment_date"].dt.to_period("M")
            trends = df.groupby("month")["amount"].sum().reset_index()
            trends["month"] = trends["month"].astype(str)
            trends_list = trends.to_dict(orient="records")
            await cache_service.set(cache_key, trends_list, self.cache_ttl)
            return {"success": True, "trends": trends_list, "cached": False}
        except Exception as e:
            logger.error(f"Failed to analyze payment trends: {e}")
            return {"success": False, "error": str(e)}

    async def get_student_performance_analytics(self, grade: Optional[str] = None) -> Dict:
        """Analyze student performance (dummy implementation, extend as needed)"""
        cache_key = f"student_performance_{grade or 'all'}"
        cached = await cache_service.get(cache_key)
        if cached:
            return {"success": True, "performance": cached, "cached": True}
        try:
            # Example: Analyze payment completion rate by grade
            filters = {"grade": grade} if grade else None
            result = await db.execute_query(
                "students",
                "select",
                filters=filters,
                select_fields=["id", "first_name", "last_name", "grade"]
            )
            if not result["success"] or not result["data"]:
                return {"success": False, "error": "No student data available"}
            students = result["data"]
            perf = []
            for student in students:
                payment_result = await db.execute_query(
                    "payments",
                    "select",
                    filters={"student_id": student["id"]},
                    select_fields=["amount", "payment_status"]
                )
                total_paid = sum([p["amount"] for p in payment_result["data"] if p["payment_status"] == "completed"]) if payment_result["success"] else 0
                perf.append({
                    "student_id": student["id"],
                    "name": f"{student['first_name']} {student['last_name']}",
                    "grade": student["grade"],
                    "total_paid": total_paid
                })
            await cache_service.set(cache_key, perf, self.cache_ttl)
            return {"success": True, "performance": perf, "cached": False}
        except Exception as e:
            logger.error(f"Failed to analyze student performance: {e}")
            return {"success": False, "error": str(e)}

    async def get_revenue_optimization_insights(self) -> Dict:
        """Provide actionable insights for revenue optimization"""
        cache_key = "revenue_optimization_insights"
        cached = await cache_service.get(cache_key)
        if cached:
            return {"success": True, "insights": cached, "cached": True}
        try:
            # Example: Identify months with lowest collection rates
            result = await db.execute_query(
                "payments",
                "select",
                select_fields=["payment_date", "amount", "payment_status"],
                order_by="payment_date ASC"
            )
            if not result["success"] or not result["data"]:
                return {"success": False, "error": "No payment data available"}
            df = pd.DataFrame(result["data"])
            df["payment_date"] = pd.to_datetime(df["payment_date"])
            df["month"] = df["payment_date"].dt.to_period("M")
            completed = df[df["payment_status"] == "completed"].groupby("month")["amount"].sum()
            all_payments = df.groupby("month")["amount"].sum()
            collection_rate = (completed / all_payments).fillna(0)
            lowest_months = collection_rate.nsmallest(3).index.astype(str).tolist()
            insights = {
                "lowest_collection_months": lowest_months,
                "collection_rates": collection_rate.round(2).to_dict()
            }
            await cache_service.set(cache_key, insights, self.cache_ttl)
            return {"success": True, "insights": insights, "cached": False}
        except Exception as e:
            logger.error(f"Failed to generate revenue optimization insights: {e}")
            return {"success": False, "error": str(e)}

    async def get_forecast_plot(self, days_ahead: int = 30) -> Dict:
        """Generate a plot of the financial forecast and return as base64 image"""
        try:
            forecast_result = await self.get_financial_forecast(days_ahead)
            if not forecast_result["success"]:
                return forecast_result
            forecast = forecast_result["forecast"]
            dates = [datetime.strptime(f["date"], "%Y-%m-%d") for f in forecast]
            amounts = [f["predicted_amount"] for f in forecast]
            plt.figure(figsize=(10, 5))
            plt.plot(dates, amounts, marker="o", label="Forecast")
            plt.title("Financial Forecast")
            plt.xlabel("Date")
            plt.ylabel("Predicted Amount")
            plt.legend()
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            plt.close()
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode("utf-8")
            return {"success": True, "image_base64": img_base64}
        except Exception as e:
            logger.error(f"Failed to generate forecast plot: {e}")
            return {"success": False, "error": str(e)}

# Initialize service
advanced_analytics_service = AdvancedAnalyticsService()
