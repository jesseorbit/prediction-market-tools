"""
Kalshi data collector using their public API.

Documentation: https://docs.kalshi.com/
API Endpoint: https://api.elections.kalshi.com/trade-api/v2
Authentication: Optional API key for higher rate limits
"""

import logging
import os
import re
import requests
from typing import List, Dict, Any
from models import StandardMarket
from utils.text_processing import normalize_title

logger = logging.getLogger(__name__)

KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"


class KalshiCollector:
    """Collector for Kalshi data."""
    
    def __init__(self, api_key: str = None, timeout: int = 30):
        """
        Initialize Kalshi collector.
        
        Args:
            api_key: Kalshi API key (optional, for authenticated requests)
            timeout: Request timeout in seconds
        """
        self.base_url = KALSHI_API_BASE
        self.timeout = timeout
        self.api_key = api_key or os.getenv("KALSHI_API_KEY")
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ArbitrageScanner/1.0",
            "Accept": "application/json",
        })
        
        # Add API key if available
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
            logger.info("Kalshi API key configured")
        else:
            logger.info("Kalshi running without API key (public data only)")
    
    def fetch_active_markets(self, limit: int = None) -> List[StandardMarket]:
        """
        Fetch active markets from Kalshi.
        
        Args:
            limit: Maximum number of markets to fetch (None = all markets)
            
        Returns:
            List of StandardMarket objects
        """
        url = f"{self.base_url}/markets"
        
        all_markets = []
        cursor = None
        
        try:
            logger.info(f"Fetching Kalshi markets...")
            
            while True:
                params = {
                    "status": "open",
                    "limit": 1000,  # Kalshi max per request
                }
                
                if cursor:
                    params["cursor"] = cursor
                
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                markets_data = data.get("markets", [])
                
                for market_data in markets_data:
                    try:
                        standard_market = self._parse_market(market_data)
                        if standard_market:
                            all_markets.append(standard_market)
                            
                            # Stop if we hit the limit
                            if limit and len(all_markets) >= limit:
                                break
                    except Exception as e:
                        logger.warning(f"Failed to parse market: {e}")
                        continue
                
                # Check if we should stop
                if limit and len(all_markets) >= limit:
                    break
                
                # Get next cursor for pagination
                cursor = data.get("cursor")
                
                # Stop if no more pages
                if not cursor:
                    break
                
                logger.debug(f"Fetched {len(all_markets)} markets so far, continuing...")
            
            logger.info(f"Fetched {len(all_markets)} Kalshi markets")
            return all_markets[:limit] if limit else all_markets
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Kalshi markets: {e}")
            return []
    
    def _parse_market(self, market: Dict[str, Any]) -> StandardMarket:
        """
        Parse a single market from Kalshi API response.
        
        Args:
            market: Market data from API
            
        Returns:
            StandardMarket object or None if parsing fails
        """
        # Extract market ticker (ID)
        ticker = market.get("ticker")
        if not ticker:
            return None
        
        # Extract title
        title = market.get("title") or market.get("subtitle", "")
        if not title:
            return None
        
        # Extract prices - Kalshi uses cents (0-100)
        # Convert to 0.0-1.0 range
        yes_price_cents = market.get("yes_price")
        no_price_cents = market.get("no_price")
        
        if yes_price_cents is not None:
            price_yes = float(yes_price_cents) / 100.0
        else:
            # Fallback
            price_yes = 0.5
        
        if no_price_cents is not None:
            price_no = float(no_price_cents) / 100.0
        else:
            # Calculate from yes price
            price_no = 1.0 - price_yes
        
        # Extract volume
        volume = float(market.get("volume", 0) or 0)
        
        # Construct market URL
        # Kalshi uses format: /markets/{event_ticker}/{event_slug}/{market_ticker}
        # We can get event_ticker from the market response
        event_ticker = market.get("event_ticker", "")
        
        if event_ticker:
            # Create a simple slug from the title (lowercase, replace spaces with hyphens)
            title_slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
            # Limit slug length
            title_slug = title_slug[:100]
            url = f"https://kalshi.com/markets/{event_ticker.lower()}/{title_slug}/{ticker.lower()}"
        else:
            # Fallback to simple format (may not work but better than nothing)
            url = f"https://kalshi.com/markets/{ticker.lower()}"
        
        # Normalize title
        normalized_title = normalize_title(title)
        
        return StandardMarket(
            platform="KALSHI",
            market_id=ticker,
            title=normalized_title,
            price_yes=price_yes,
            price_no=price_no,
            volume=volume,
            url=url,
        )
