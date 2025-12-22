"""
Polymarket data collector using Gamma API.

Documentation: https://docs.polymarket.com/#gamma-markets-api
"""

import logging
import requests
from typing import List, Dict, Any
from datetime import datetime
from models import StandardMarket
from utils.text_processing import normalize_title

logger = logging.getLogger(__name__)

GAMMA_API_BASE = "https://gamma-api.polymarket.com"


class PolymarketCollector:
    """Collector for Polymarket data via Gamma API."""
    
    def __init__(self, timeout: int = 30):
        """
        Initialize Polymarket collector.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.base_url = GAMMA_API_BASE
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ArbitrageScanner/1.0",
            "Accept": "application/json",
        })
    
    def fetch_active_markets(self, limit: int = None) -> List[StandardMarket]:
        """
        Fetch active markets from Polymarket using pagination.
        Only fetches markets that end in the future.
        
        Args:
            limit: Maximum number of markets to fetch (None = all markets)
            
        Returns:
            List of StandardMarket objects
        """
        url = f"{self.base_url}/events"
        
        all_markets = []
        offset = 0
        batch_size = 100  # Fetch 100 events per request
        
        try:
            logger.info(f"Fetching active Polymarket markets (future markets only)...")
            
            while True:
                params = {
                    "active": "true",
                    "closed": "false",
                    "limit": batch_size,
                    "offset": offset,
                }
                
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                events = response.json()
                
                # Stop if no more events
                if not events:
                    break
                
                for event in events:
                    # Each event can have multiple markets
                    event_markets = event.get("markets", [])
                    
                    for market in event_markets:
                        try:
                            # Filter: only active, non-closed markets
                            if market.get("closed") == True:
                                continue
                            if market.get("active") == False:
                                continue
                            
                            # CRITICAL: Filter out past markets
                            # Only get markets ending in the future
                            end_date = market.get("end_date_iso")
                            if end_date:
                                try:
                                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                                    now = datetime.now(end_dt.tzinfo)
                                    if end_dt < now:
                                        continue  # Skip past markets
                                except:
                                    pass  # If parsing fails, include the market
                            
                            standard_market = self._parse_market(market, event)
                            if standard_market:
                                all_markets.append(standard_market)
                                
                                # Stop if we hit the limit
                                if limit and len(all_markets) >= limit:
                                    logger.info(f"Fetched {len(all_markets)} Polymarket markets (limit reached)")
                                    return all_markets
                        except Exception as e:
                            logger.warning(f"Failed to parse market: {e}")
                            continue
                
                # Move to next page
                offset += batch_size
                logger.debug(f"Fetched {len(all_markets)} markets so far, offset={offset}")
                
                # Safety check: if we got fewer events than batch_size, we're at the end
                if len(events) < batch_size:
                    break
            
            logger.info(f"Fetched {len(all_markets)} active Polymarket markets")
            return all_markets
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Polymarket markets: {e}")
            return []
    
    def _parse_market(self, market: Dict[str, Any], event: Dict[str, Any]) -> StandardMarket:
        """
        Parse a single market from Gamma API response.
        
        Args:
            market: Market data from API
            event: Parent event data
            
        Returns:
            StandardMarket object or None if parsing fails
        """
        # Extract market ID
        market_id = market.get("id") or market.get("conditionId")
        if not market_id:
            return None
        
        # Extract title (use market question or event title)
        title = market.get("question") or event.get("title", "")
        if not title:
            return None
        
        # Extract outcome prices - handle multiple formats
        outcome_prices = market.get("outcomePrices", [])
        
        # If it's a string, try to parse as JSON
        if isinstance(outcome_prices, str):
            try:
                import json
                outcome_prices = json.loads(outcome_prices)
            except:
                outcome_prices = []
        
        # Ensure it's a list
        if not isinstance(outcome_prices, list):
            outcome_prices = []
        
        # Try to extract prices
        if len(outcome_prices) >= 2:
            try:
                # Index 0 = Yes, Index 1 = No
                price_yes = float(outcome_prices[0])
                price_no = float(outcome_prices[1])
            except (ValueError, TypeError):
                # Fallback if conversion fails
                price_yes = 0.5
                price_no = 0.5
        else:
            # Fallback: try to get from other fields
            price_yes = float(market.get("price", 0.5))
            price_no = 1.0 - price_yes
        
        # Extract volume (convert to float, default to 0)
        volume = float(market.get("volume", 0) or 0)
        
        # Construct market URL
        slug = event.get("slug", market_id)
        url = f"https://polymarket.com/event/{slug}"
        
        # Normalize title
        normalized_title = normalize_title(title)
        
        return StandardMarket(
            platform="POLY",
            market_id=market_id,
            title=normalized_title,
            price_yes=price_yes,
            price_no=price_no,
            volume=volume,
            url=url,
        )
