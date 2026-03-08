"""
Opportunity Queue + Priority Scheduler

Features:
- FIFO + score-based sorting
- Batch processing
- Dependency tracking
- Rate limiting

Target: Process opportunities efficiently while respecting constraints
"""
import asyncio
import heapq
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class QueuedOpportunity:
    """Opportunity in the queue"""
    id: str
    score: float
    strategy_name: str
    token_path: List[str]
    pool_addresses: List[str]
    expected_profit_usd: float
    required_capital_usd: float
    confidence: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    status: str = "pending"  # pending, processing, executed, expired, cancelled
    priority: int = 0  # Higher = more urgent
    dependencies: Set[str] = field(default_factory=set)
    
    def __lt__(self, other):
        """For heap comparison - higher score first"""
        return self.score > other.score
    
    def is_expired(self) -> bool:
        """Check if opportunity has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "score": self.score,
            "strategy_name": self.strategy_name,
            "token_path": self.token_path,
            "pool_addresses": self.pool_addresses,
            "expected_profit_usd": self.expected_profit_usd,
            "required_capital_usd": self.required_capital_usd,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
            "priority": self.priority,
            "dependencies": list(self.dependencies),
        }


@dataclass
class SchedulerConfig:
    """Configuration for the scheduler"""
    max_queue_size: int = 1000
    batch_size: int = 10
    max_concurrent: int = 3
    processing_interval_ms: int = 100
    opportunity_ttl_ms: int = 5000
    rate_limit_per_second: int = 20


class OpportunityQueue:
    """
    Priority queue for opportunities
    
    Features:
    - Max-heap by score
    - Automatic expiration
    - Dependency tracking
    """
    
    def __init__(self, config: SchedulerConfig = None):
        if config is None:
            config = SchedulerConfig()
        
        self.config = config
        self._heap: List[QueuedOpportunity] = []
        self._by_id: Dict[str, QueuedOpportunity] = {}
        self._lock = asyncio.Lock()
    
    async def push(self, opportunity: QueuedOpportunity) -> bool:
        """
        Add opportunity to queue
        
        Returns:
            True if added, False if queue full
        """
        async with self._lock:
            if len(self._by_id) >= self.config.max_queue_size:
                return False
            
            # Set expiration if not set
            if opportunity.expires_at is None:
                ttl_seconds = self.config.opportunity_ttl_ms / 1000
                opportunity.expires_at = datetime.utcnow().replace(
                    microsecond=0
                ) + asyncio.get_event_loop().call_later(
                    ttl_seconds, lambda: None
                ) if hasattr(asyncio.get_event_loop(), 'call_later') else None
                # Simpler approach:
                from datetime import timedelta
                opportunity.expires_at = datetime.utcnow() + timedelta(
                    milliseconds=self.config.opportunity_ttl_ms
                )
            
            heapq.heappush(self._heap, opportunity)
            self._by_id[opportunity.id] = opportunity
            return True
    
    async def pop(self) -> Optional[QueuedOpportunity]:
        """
        Get highest priority opportunity
        
        Returns:
            QueuedOpportunity or None
        """
        async with self._lock:
            while self._heap:
                opp = heapq.heappop(self._heap)
                
                # Remove if expired
                if opp.is_expired():
                    self._by_id.pop(opp.id, None)
                    continue
                
                # Remove if already processed
                if opp.status != "pending":
                    self._by_id.pop(opp.id, None)
                    continue
                
                return opp
            
            return None
    
    async def peek(self) -> Optional[QueuedOpportunity]:
        """Get highest priority opportunity without removing"""
        async with self._lock:
            while self._heap:
                opp = self._heap[0]
                
                if opp.is_expired() or opp.status != "pending":
                    heapq.heappop(self._heap)
                    self._by_id.pop(opp.id, None)
                    continue
                
                return opp
            
            return None
    
    async def remove(self, opportunity_id: str) -> bool:
        """Remove opportunity by ID"""
        async with self._lock:
            if opportunity_id in self._by_id:
                opp = self._by_id.pop(opportunity_id)
                opp.status = "cancelled"
                return True
            return False
    
    async def update_status(
        self,
        opportunity_id: str,
        status: str,
    ) -> bool:
        """Update opportunity status"""
        async with self._lock:
            if opportunity_id in self._by_id:
                self._by_id[opportunity_id].status = status
                return True
            return False
    
    async def get_batch(self, batch_size: int = None) -> List[QueuedOpportunity]:
        """Get batch of opportunities for processing"""
        if batch_size is None:
            batch_size = self.config.batch_size
        
        batch = []
        
        async with self._lock:
            while len(batch) < batch_size and self._heap:
                opp = heapq.heappop(self._heap)
                
                if opp.is_expired() or opp.status != "pending":
                    self._by_id.pop(opp.id, None)
                    continue
                
                # Check dependencies
                if opp.dependencies:
                    deps_met = all(
                        self._by_id.get(dep_id, QueuedOpportunity(
                            id="", score=0, strategy_name="",
                            token_path=[], pool_addresses=[],
                            expected_profit_usd=0, required_capital_usd=0,
                            confidence=0,
                        )).status == "executed"
                        for dep_id in opp.dependencies
                    )
                    
                    if not deps_met:
                        # Re-queue for later
                        heapq.heappush(self._heap, opp)
                        continue
                
                batch.append(opp)
                opp.status = "processing"
        
        return batch
    
    async def size(self) -> int:
        """Get current queue size"""
        async with self._lock:
            return len(self._by_id)
    
    async def clear_expired(self) -> int:
        """Remove all expired opportunities"""
        async with self._lock:
            expired_ids = [
                opp_id for opp_id, opp in self._by_id.items()
                if opp.is_expired()
            ]
            
            for opp_id in expired_ids:
                opp = self._by_id.pop(opp_id)
                opp.status = "expired"
            
            # Rebuild heap without expired
            self._heap = [
                opp for opp in self._heap
                if not opp.is_expired() and opp.id in self._by_id
            ]
            heapq.heapify(self._heap)
            
            return len(expired_ids)
    
    def get_statistics(self) -> Dict:
        """Get queue statistics"""
        pending = sum(1 for opp in self._by_id.values() if opp.status == "pending")
        processing = sum(1 for opp in self._by_id.values() if opp.status == "processing")
        executed = sum(1 for opp in self._by_id.values() if opp.status == "executed")
        expired = sum(1 for opp in self._by_id.values() if opp.status == "expired")
        
        return {
            "total": len(self._by_id),
            "pending": pending,
            "processing": processing,
            "executed": executed,
            "expired": expired,
            "max_size": self.config.max_queue_size,
            "utilization": len(self._by_id) / self.config.max_queue_size * 100,
        }


class PriorityScheduler:
    """
    Priority scheduler for opportunity processing
    
    Features:
    - Configurable processing interval
    - Rate limiting
    - Concurrent execution
    - Statistics tracking
    """
    
    def __init__(
        self,
        queue: OpportunityQueue,
        config: SchedulerConfig = None,
    ):
        if config is None:
            config = SchedulerConfig()
        
        self.queue = queue
        self.config = config
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
        # Statistics
        self.processed_count = 0
        self.failed_count = 0
        self.total_profit_usd = 0.0
        self.last_process_time: Optional[datetime] = None
    
    async def start(self):
        """Start scheduler loop"""
        self.running = True
        self._task = asyncio.create_task(self._run_loop())
    
    async def stop(self):
        """Stop scheduler loop"""
        self.running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _run_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                # Get batch of opportunities
                batch = await self.queue.get_batch()
                
                if batch:
                    # Process batch
                    await self._process_batch(batch)
                
                # Clear expired opportunities periodically
                await self.queue.clear_expired()
                
                # Wait for next interval
                await asyncio.sleep(self.config.processing_interval_ms / 1000)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Scheduler error: {e}")
                await asyncio.sleep(1)  # Backoff on error
    
    async def _process_batch(self, batch: List[QueuedOpportunity]):
        """Process a batch of opportunities"""
        # Limit concurrent execution
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
        async def process_one(opp: QueuedOpportunity):
            async with semaphore:
                try:
                    # Execute opportunity (placeholder - real execution elsewhere)
                    success, profit = await self._execute_opportunity(opp)
                    
                    # Update statistics
                    self.processed_count += 1
                    if success:
                        self.total_profit_usd += profit
                    else:
                        self.failed_count += 1
                    
                    # Update status
                    status = "executed" if success else "failed"
                    await self.queue.update_status(opp.id, status)
                    
                except Exception as e:
                    print(f"Error processing {opp.id}: {e}")
                    self.failed_count += 1
                    await self.queue.update_status(opp.id, "failed")
        
        # Process all in batch concurrently
        await asyncio.gather(*[process_one(opp) for opp in batch])
        
        self.last_process_time = datetime.utcnow()
    
    async def _execute_opportunity(
        self,
        opportunity: QueuedOpportunity,
    ) -> Tuple[bool, float]:
        """
        Execute opportunity (placeholder)
        
        In production, this would:
        1. Build transaction/bundle
        2. Simulate execution
        3. Submit to network
        4. Wait for confirmation
        
        Returns:
            (success, profit_usd)
        """
        # Placeholder - always succeeds with expected profit
        await asyncio.sleep(0.1)  # Simulate execution time
        return True, opportunity.expected_profit_usd
    
    def get_statistics(self) -> Dict:
        """Get scheduler statistics"""
        queue_stats = self.queue.get_statistics()
        
        success_rate = (
            self.processed_count / (self.processed_count + self.failed_count) * 100
            if (self.processed_count + self.failed_count) > 0 else 0
        )
        
        return {
            **queue_stats,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "success_rate": success_rate,
            "total_profit_usd": self.total_profit_usd,
            "last_process_time": (
                self.last_process_time.isoformat() if self.last_process_time else None
            ),
            "running": self.running,
        }
