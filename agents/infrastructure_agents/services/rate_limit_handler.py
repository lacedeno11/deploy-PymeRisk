"""
Rate Limit Handler para Azure OpenAI Service
Maneja automáticamente los rate limits con retry y backoff exponencial
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class RateLimitConfig:
    """Configuración para manejo de rate limits"""
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    rate_limit_window: int = 60  # seconds
    max_requests_per_window: int = 50
    
class RateLimitHandler:
    """
    Maneja rate limits con estrategias inteligentes de retry
    """
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.logger = logging.getLogger(__name__)
        self.request_history = []
        self.last_rate_limit_time = None
        
    async def execute_with_retry(self, 
                                func: Callable,
                                *args,
                                **kwargs) -> Any:
        """
        Ejecuta una función con retry automático en caso de rate limit
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Check if we should wait before making the request
                await self._wait_if_needed()
                
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Record successful request
                self._record_request(success=True)
                
                if attempt > 0:
                    self.logger.info(f"Request succeeded after {attempt} retries")
                
                return result
                
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                if self._is_rate_limit_error(error_str):
                    self.logger.warning(f"Rate limit hit on attempt {attempt + 1}/{self.config.max_retries + 1}")
                    self._record_request(success=False)
                    self.last_rate_limit_time = datetime.now()
                    
                    if attempt < self.config.max_retries:
                        delay = self._calculate_delay(attempt, error_str)
                        self.logger.info(f"Waiting {delay:.2f} seconds before retry...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        self.logger.error(f"Max retries ({self.config.max_retries}) exceeded for rate limit")
                        break
                        
                # Check if it's a temporary API error
                elif self._is_temporary_error(error_str):
                    self.logger.warning(f"Temporary API error on attempt {attempt + 1}: {str(e)}")
                    
                    if attempt < self.config.max_retries:
                        delay = self._calculate_delay(attempt, error_str, is_api_error=True)
                        self.logger.info(f"Waiting {delay:.2f} seconds before retry...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        self.logger.error(f"Max retries exceeded for API error")
                        break
                        
                else:
                    # Not a retryable error
                    self.logger.error(f"Non-retryable error: {str(e)}")
                    raise e
        
        # If we get here, all retries failed
        raise last_exception
    
    def _is_rate_limit_error(self, error_str: str) -> bool:
        """Detecta si el error es de rate limit"""
        rate_limit_indicators = [
            "rate limit",
            "429",
            "quota",
            "too many requests",
            "requests per minute",
            "throttled",
            "exceeded call rate limit"
        ]
        
        return any(indicator in error_str for indicator in rate_limit_indicators)
    
    def _is_temporary_error(self, error_str: str) -> bool:
        """Detecta si el error es temporal y se puede reintentar"""
        temporary_indicators = [
            "timeout",
            "connection",
            "network",
            "502",
            "503",
            "504",
            "internal server error",
            "service unavailable",
            "gateway timeout"
        ]
        
        return any(indicator in error_str for indicator in temporary_indicators)
    
    def _calculate_delay(self, attempt: int, error_str: str, is_api_error: bool = False) -> float:
        """Calcula el delay para el siguiente intento"""
        
        # Extract suggested delay from error message if available
        suggested_delay = self._extract_suggested_delay(error_str)
        if suggested_delay:
            base_delay = suggested_delay
        else:
            base_delay = self.config.base_delay
        
        # Calculate exponential backoff
        if is_api_error:
            # Shorter delays for API errors
            delay = base_delay * (1.5 ** attempt)
        else:
            # Longer delays for rate limits
            delay = base_delay * (self.config.exponential_base ** attempt)
        
        # Cap the delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to avoid thundering herd
        if self.config.jitter:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(delay, 0.1)  # Minimum 0.1 second delay
    
    def _extract_suggested_delay(self, error_str: str) -> Optional[float]:
        """Extrae el delay sugerido del mensaje de error"""
        import re
        
        # Look for "retry after X seconds" patterns
        patterns = [
            r"retry after (\d+) seconds?",
            r"please retry after (\d+) seconds?",
            r"wait (\d+) seconds?",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_str, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return None
    
    async def _wait_if_needed(self):
        """Espera si es necesario basado en el historial de requests"""
        current_time = datetime.now()
        
        # Clean old requests from history
        cutoff_time = current_time - timedelta(seconds=self.config.rate_limit_window)
        self.request_history = [
            req_time for req_time in self.request_history 
            if req_time > cutoff_time
        ]
        
        # Check if we're approaching the rate limit
        if len(self.request_history) >= self.config.max_requests_per_window * 0.8:  # 80% of limit
            # Calculate time to wait
            oldest_request = min(self.request_history)
            wait_time = (oldest_request + timedelta(seconds=self.config.rate_limit_window) - current_time).total_seconds()
            
            if wait_time > 0:
                self.logger.info(f"Proactively waiting {wait_time:.2f} seconds to avoid rate limit")
                await asyncio.sleep(wait_time)
        
        # Extra wait if we recently hit a rate limit
        if self.last_rate_limit_time:
            time_since_rate_limit = (current_time - self.last_rate_limit_time).total_seconds()
            if time_since_rate_limit < 10:  # Wait extra if rate limit was recent
                extra_wait = 10 - time_since_rate_limit
                self.logger.info(f"Extra wait of {extra_wait:.2f} seconds due to recent rate limit")
                await asyncio.sleep(extra_wait)
    
    def _record_request(self, success: bool):
        """Registra un request en el historial"""
        self.request_history.append(datetime.now())
        
        # Keep only recent requests
        cutoff_time = datetime.now() - timedelta(seconds=self.config.rate_limit_window * 2)
        self.request_history = [
            req_time for req_time in self.request_history 
            if req_time > cutoff_time
        ]
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de rate limiting"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(seconds=self.config.rate_limit_window)
        
        recent_requests = [
            req_time for req_time in self.request_history 
            if req_time > cutoff_time
        ]
        
        return {
            "requests_in_current_window": len(recent_requests),
            "max_requests_per_window": self.config.max_requests_per_window,
            "utilization_percentage": (len(recent_requests) / self.config.max_requests_per_window) * 100,
            "last_rate_limit_time": self.last_rate_limit_time.isoformat() if self.last_rate_limit_time else None,
            "time_since_last_rate_limit": (current_time - self.last_rate_limit_time).total_seconds() if self.last_rate_limit_time else None
        }

class SmartRateLimiter:
    """
    Rate limiter inteligente que se adapta dinámicamente
    """
    
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.current_delay = 1.0
        self.adaptive_factor = 1.0
        self.logger = logging.getLogger(__name__)
    
    async def adaptive_delay(self):
        """Aplica delay adaptivo basado en el historial de éxito/fallo"""
        
        # Calculate success rate
        total_requests = self.success_count + self.failure_count
        if total_requests > 0:
            success_rate = self.success_count / total_requests
            
            # Adjust adaptive factor based on success rate
            if success_rate > 0.9:  # High success rate
                self.adaptive_factor = max(0.5, self.adaptive_factor * 0.9)  # Reduce delay
            elif success_rate < 0.7:  # Low success rate
                self.adaptive_factor = min(3.0, self.adaptive_factor * 1.2)  # Increase delay
        
        # Apply adaptive delay
        delay = self.current_delay * self.adaptive_factor
        
        if delay > 0.1:
            self.logger.debug(f"Applying adaptive delay: {delay:.2f}s (factor: {self.adaptive_factor:.2f})")
            await asyncio.sleep(delay)
    
    def record_success(self):
        """Registra un request exitoso"""
        self.success_count += 1
        
        # Reset counters periodically to adapt to changing conditions
        if (self.success_count + self.failure_count) > 100:
            self.success_count = int(self.success_count * 0.8)
            self.failure_count = int(self.failure_count * 0.8)
    
    def record_failure(self):
        """Registra un request fallido"""
        self.failure_count += 1
        
        # Reset counters periodically
        if (self.success_count + self.failure_count) > 100:
            self.success_count = int(self.success_count * 0.8)
            self.failure_count = int(self.failure_count * 0.8)

# Global rate limiter instance
global_rate_limiter = SmartRateLimiter()