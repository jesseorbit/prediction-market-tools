"""
Opinion Labs data collector using their public API.

Documentation: https://docs.opinion.trade/api
API Endpoint: https://proxy.opinion.trade:8443/openapi/market
Authentication: Requires API key in 'apikey' header
"""

import logging
import os
import requests
from typing import List, Dict, Any, Optional
from models import StandardMarket
from utils.text_processing import normalize_title

logger = logging.getLogger(__name__)

OPINION_API_BASE = "https://proxy.opinion.trade:8443/openapi"


class OpinionCollector:
    """Collector for Opinion Labs data."""
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize Opinion Labs collector.
        
        Args:
            api_key: Opinion Labs API key (or set OPINION_API_KEY env var)
            timeout: Request timeout in seconds
        """
        self.base_url = OPINION_API_BASE
        self.timeout = timeout
        
        # Get API key from parameter or environment variable
        self.api_key = api_key or os.getenv("OPINION_API_KEY")
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ArbitrageScanner/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        
        # Add API key to headers if available
        if self.api_key:
            self.session.headers.update({
                "apikey": self.api_key
            })
            logger.info("Opinion Labs API key configured")
        else:
            logger.warning(
                "No Opinion Labs API key provided. "
                "Set OPINION_API_KEY environment variable or pass api_key parameter. "
                "Get your API key at: https://docs.opinion.trade/"
            )
    
    def fetch_active_markets(self, limit: int = 100) -> List[StandardMarket]:
        """
        Fetch active markets from Opinion Labs.
        
        Args:
            limit: Maximum number of markets to fetch
            
        Returns:
            List of StandardMarket objects
        """
        # Opinion Labs endpoint: /openapi/market
        url = f"{self.base_url}/market"
        params = {
            "limit": limit,
        }
        
        try:
            logger.info(f"Fetching Opinion Labs markets (limit={limit})...")
            
            if not self.api_key:
                logger.error("Cannot fetch markets: API key not configured")
                return []
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, dict):
                markets_data = data.get("markets", data.get("data", data.get("result", [])))
            else:
                markets_data = data
            
            markets = []
            
            for market_data in markets_data:
                try:
                    standard_market = self._parse_market(market_data)
                    if standard_market:
                        markets.append(standard_market)
                except Exception as e:
                    logger.warning(f"Failed to parse market: {e}")
                    continue
            
            logger.info(f"Fetched {len(markets)} Opinion Labs markets")
            return markets
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Opinion Labs markets: {e}")
            return []
    
    def _parse_market(self, market: Dict[str, Any]) -> StandardMarket:
        """
        Parse a single market from Opinion API response.
        
        Args:
            market: Market data from API
            
        Returns:
            StandardMarket object or None if parsing fails
        """
        # Extract market ID
        market_id = market.get("marketId") or market.get("id")
        if not market_id:
            return None
        
        # Extract title
        title = market.get("question") or market.get("title", "")
        if not title:
            return None
        
        # Extract prices
        # Try direct yes/no price fields first
        price_yes = market.get("yes_price") or market.get("yesPrice")
        price_no = market.get("no_price") or market.get("noPrice")
        
        # If not available, try probability field
        if price_yes is None:
            probability = market.get("probability")
            if probability is not None:
                price_yes = float(probability)
                price_no = 1.0 - price_yes
            else:
                # Fallback to 0.5/0.5
                price_yes = 0.5
                price_no = 0.5
        else:
            price_yes = float(price_yes)
            price_no = float(price_no) if price_no is not None else (1.0 - price_yes)
        
        # Extract volume
        volume = float(market.get("volume", 0) or market.get("totalVolume", 0) or 0)
        
        # Construct market URL
        slug = market.get("slug", market_id)
        url = f"https://opinion.trade/market/{slug}"
        
        # Normalize title
        normalized_title = normalize_title(title)
        
        return StandardMarket(
            platform="OPINION",
            market_id=str(market_id),
            title=normalized_title,
            price_yes=price_yes,
            price_no=price_no,
            volume=volume,
            url=url,
        )
