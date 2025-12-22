"""
Fuzzy matching engine for identifying similar markets across platforms.
"""

import logging
from typing import List, Tuple
from rapidfuzz import fuzz
from models import StandardMarket, ArbitrageOpportunity
from utils.text_processing import has_common_keywords

logger = logging.getLogger(__name__)


class MarketMatcher:
    """Fuzzy matching engine for cross-platform market identification."""
    
    def __init__(self, similarity_threshold: float = 85.0, min_common_keywords: int = 2):
        """
        Initialize market matcher.
        
        Args:
            similarity_threshold: Minimum similarity score (0-100) to consider a match
            min_common_keywords: Minimum number of common keywords required
        """
        self.similarity_threshold = similarity_threshold
        self.min_common_keywords = min_common_keywords
    
    def find_matches(
        self, 
        poly_markets: List[StandardMarket], 
        opinion_markets: List[StandardMarket]
    ) -> List[Tuple[StandardMarket, StandardMarket, float]]:
        """
        Find matching markets between Polymarket and Opinion Labs.
        
        Args:
            poly_markets: List of Polymarket markets
            opinion_markets: List of Opinion Labs markets
            
        Returns:
            List of tuples (poly_market, opinion_market, similarity_score)
        """
        matches = []
        
        logger.info(f"Matching {len(poly_markets)} Polymarket vs {len(opinion_markets)} Opinion markets...")
        
        for poly_market in poly_markets:
            best_match = None
            best_score = 0.0
            
            for opinion_market in opinion_markets:
                # Calculate similarity score using token_sort_ratio
                # This handles word order differences well
                score = fuzz.token_sort_ratio(
                    poly_market.title, 
                    opinion_market.title
                )
                
                # Additional validation: check for common keywords
                if score >= self.similarity_threshold:
                    if has_common_keywords(
                        poly_market.title, 
                        opinion_market.title, 
                        self.min_common_keywords
                    ):
                        if score > best_score:
                            best_score = score
                            best_match = opinion_market
            
            if best_match:
                matches.append((poly_market, best_match, best_score))
                logger.debug(
                    f"Match found (score={best_score:.1f}): "
                    f"{poly_market.title[:40]} <-> {best_match.title[:40]}"
                )
        
        logger.info(f"Found {len(matches)} matching pairs")
        return matches
    
    def calculate_arbitrage(
        self, 
        matches: List[Tuple[StandardMarket, StandardMarket, float]],
        min_margin: float = 0.02,
        max_cost: float = 0.98
    ) -> List[ArbitrageOpportunity]:
        """
        Calculate arbitrage opportunities from matched pairs.
        
        Strategy: Buy Yes on one platform, No on the other.
        Total cost should be < 1.0 to guarantee profit.
        
        Args:
            matches: List of matched market pairs
            min_margin: Minimum profit margin required (default 2%)
            max_cost: Maximum total cost allowed (default 0.98)
            
        Returns:
            List of ArbitrageOpportunity objects, sorted by ROI descending
        """
        opportunities = []
        
        logger.info(f"Calculating arbitrage for {len(matches)} matched pairs...")
        
        for poly_market, opinion_market, similarity_score in matches:
            # Strategy 1: Buy Poly Yes + Opinion No
            cost_1 = poly_market.price_yes + opinion_market.price_no
            
            # Strategy 2: Buy Poly No + Opinion Yes
            cost_2 = poly_market.price_no + opinion_market.price_yes
            
            # Choose the cheaper strategy
            if cost_1 < cost_2:
                total_cost = cost_1
                strategy = "Poly YES + Opinion NO"
            else:
                total_cost = cost_2
                strategy = "Poly NO + Opinion YES"
            
            # Check if arbitrage exists
            if total_cost <= max_cost:
                profit_margin = 1.0 - total_cost
                
                if profit_margin >= min_margin:
                    roi_percent = (profit_margin / total_cost) * 100
                    
                    opportunity = ArbitrageOpportunity(
                        poly_market=poly_market,
                        opinion_market=opinion_market,
                        similarity_score=similarity_score,
                        total_cost=total_cost,
                        profit_margin=profit_margin,
                        roi_percent=roi_percent,
                    )
                    
                    opportunities.append(opportunity)
                    logger.info(
                        f"Arbitrage found! ROI={roi_percent:.2f}%, "
                        f"Cost=${total_cost:.4f}, Strategy={strategy}"
                    )
        
        # Sort by ROI descending
        opportunities.sort(key=lambda x: x.roi_percent, reverse=True)
        
        logger.info(f"Found {len(opportunities)} arbitrage opportunities")
        return opportunities
