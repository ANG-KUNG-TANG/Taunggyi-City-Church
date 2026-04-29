# """
# Production Metrics System
# Features:
# - Prometheus metrics collection
# - Custom metrics for business logic
# - Performance monitoring
# - Health checks
# - Alerting rules
# """

# import time
# import logging
# from typing import Dict, Any, Optional, Callable
# from contextlib import contextmanager
# from datetime import datetime
# from dataclasses import dataclass
# from enum import Enum

# from prometheus_client import (
#     Counter, Histogram, Gauge, Summary, 
#     generate_latest, CONTENT_TYPE_LATEST,
#     CollectorRegistry, multiprocess, start_http_server
# )
# from prometheus_client.exposition import MetricsHandler
# from django.conf import settings
# from django.http import HttpResponse

# logger = logging.getLogger(__name__)

# # ============ METRICS REGISTRY ============

# class MetricsRegistry:
#     """Central registry for all application metrics"""
    
#     _instance = None
    
#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#             cls._instance._initialize()
#         return cls._instance
    
#     def _initialize(self):
#         """Initialize metrics registry"""
#         # Use multiprocess registry for Django with multiple workers
#         if getattr(settings, 'PROMETHEUS_MULTIPROC_MODE', False):
#             self.registry = CollectorRegistry()
#             multiprocess.MultiProcessCollector(self.registry)
#         else:
#             self.registry = CollectorRegistry()
        
#         self._metrics = {}
#         self._labels_cache = {}
        
#         # Initialize core metrics
#         self._init_core_metrics()
    
#     def _init_core_metrics(self):
#         """Initialize core application metrics"""
        
#         # HTTP Metrics
#         self.http_requests_total = Counter(
#             'http_requests_total',
#             'Total HTTP requests',
#             ['method', 'endpoint', 'status', 'client'],
#             registry=self.registry
#         )
        
#         self.http_request_duration = Histogram(
#             'http_request_duration_seconds',
#             'HTTP request duration in seconds',
#             ['method', 'endpoint', 'status'],
#             buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
#             registry=self.registry
#         )
        
#         # Database Metrics
#         self.db_queries_total = Counter(
#             'db_queries_total',
#             'Total database queries',
#             ['operation', 'table', 'status'],
#             registry=self.registry
#         )
        
#         self.db_query_duration = Histogram(
#             'db_query_duration_seconds',
#             'Database query duration in seconds',
#             ['operation', 'table'],
#             buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
#             registry=self.registry
#         )
        
#         # Cache Metrics
#         self.cache_operations_total = Counter(
#             'cache_operations_total',
#             'Total cache operations',
#             ['operation', 'cache_name', 'status'],
#             registry=self.registry
#         )
        
#         self.cache_hit_ratio = Gauge(
#             'cache_hit_ratio',
#             'Cache hit ratio',
#             ['cache_name'],
#             registry=self.registry
#         )
        
#         # Business Metrics
#         self.user_registrations_total = Counter(
#             'user_registrations_total',
#             'Total user registrations',
#             ['source', 'status'],
#             registry=self.registry
#         )
        
#         self.user_logins_total = Counter(
#             'user_logins_total',
#             'Total user logins',
#             ['status', 'method'],
#             registry=self.registry
#         )
        
#         self.api_calls_total = Counter(
#             'api_calls_total',
#             'Total API calls',
#             ['service', 'endpoint', 'status'],
#             registry=self.registry
#         )
        
#         # Performance Metrics
#         self.memory_usage = Gauge(
#             'memory_usage_bytes',
#             'Memory usage in bytes',
#             ['type'],
#             registry=self.registry
#         )
        
#         self.cpu_usage = Gauge(
#             'cpu_usage_percent',
#             'CPU usage percentage',
#             registry=self.registry
#         )
        
#         # Error Metrics
#         self.errors_total = Counter(
#             'errors_total',
#             'Total errors',
#             ['type', 'source', 'severity'],
#             registry=self.registry
#         )
        
#         # Custom Business Metrics
#         self.active_users = Gauge(
#             'active_users_total',
#             'Number of active users',
#             registry=self.registry
#         )
        
#         self.concurrent_requests = Gauge(
#             'concurrent_requests',
#             'Number of concurrent requests',
#             registry=self.registry
#         )
        
#         self.request_queue_size = Gauge(
#             'request_queue_size',
#             'Request queue size',
#             registry=self.registry
#         )
    
#     # ============ METRICS UTILITIES ============
    
#     @contextmanager
#     def measure_duration(self, metric: Histogram, labels: Dict[str, str] = None):
#         """Context manager to measure operation duration"""
#         start_time = time.time()
#         try:
#             yield
#         finally:
#             duration = time.time() - start_time
#             if labels:
#                 metric.labels(**labels).observe(duration)
#             else:
#                 metric.observe(duration)
    
#     def increment_counter(self, metric: Counter, labels: Dict[str, str] = None, value: int = 1):
#         """Increment a counter metric"""
#         if labels:
#             metric.labels(**labels).inc(value)
#         else:
#             metric.inc(value)
    
#     def set_gauge(self, metric: Gauge, value: float, labels: Dict[str, str] = None):
#         """Set a gauge metric value"""
#         if labels:
#             metric.labels(**labels).set(value)
#         else:
#             metric.set(value)
    
#     def observe_histogram(self, metric: Histogram, value: float, labels: Dict[str, str] = None):
#         """Observe a histogram metric"""
#         if labels:
#             metric.labels(**labels).observe(value)
#         else:
#             metric.observe(value)
    
#     # ============ METRICS MIDDLEWARE ============
    
#     class MetricsMiddleware:
#         """Django middleware for HTTP metrics"""
        
#         def __init__(self, get_response):
#             self.get_response = get_response
#             self.registry = MetricsRegistry()
        
#         def __call__(self, request):
#             # Skip metrics endpoint
#             if request.path == '/metrics':
#                 return self.get_response(request)
            
#             start_time = time.time()
            
#             try:
#                 response = self.get_response(request)
                
#                 # Record metrics
#                 duration = time.time() - start_time
                
#                 self.registry.http_requests_total.labels(
#                     method=request.method,
#                     endpoint=self._get_endpoint_name(request),
#                     status=response.status_code,
#                     client=self._get_client_ip(request)
#                 ).inc()
                
#                 self.registry.http_request_duration.labels(
#                     method=request.method,
#                     endpoint=self._get_endpoint_name(request),
#                     status=response.status_code
#                 ).observe(duration)
                
#                 return response
                
#             except Exception as e:
#                 # Record error metrics
#                 self.registry.errors_total.labels(
#                     type=type(e).__name__,
#                     source='http',
#                     severity='error'
#                 ).inc()
#                 raise
        
#         def _get_endpoint_name(self, request):
#             """Extract endpoint name from request"""
#             path = request.path
#             # Remove version prefix if present
#             if path.startswith('/api/v'):
#                 path = path.split('/')[3:]
#                 return '/'.join(path) if path else 'root'
#             return path
        
#         def _get_client_ip(self, request):
#             """Extract client IP from request"""
#             x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#             if x_forwarded_for:
#                 return x_forwarded_for.split(',')[0]
#             return request.META.get('REMOTE_ADDR', 'unknown')
    
#     # ============ HEALTH CHECK METRICS ============
    
#     def record_health_check(self, service: str, status: str, duration: float = None):
#         """Record health check metrics"""
#         health_check_status = Gauge(
#             f'health_check_{service}',
#             f'Health check status for {service}',
#             registry=self.registry
#         )
        
#         status_value = 1 if status == 'healthy' else 0
#         health_check_status.set(status_value)
        
#         if duration is not None:
#             health_check_duration = Histogram(
#                 f'health_check_duration_seconds',
#                 f'Health check duration for {service}',
#                 ['service'],
#                 registry=self.registry
#             )
#             health_check_duration.labels(service=service).observe(duration)
    
#     # ============ BUSINESS METRICS ============
    
#     def record_user_registration(self, source: str, status: str):
#         """Record user registration metrics"""
#         self.user_registrations_total.labels(
#             source=source,
#             status=status
#         ).inc()
    
#     def record_user_login(self, status: str, method: str = 'password'):
#         """Record user login metrics"""
#         self.user_logins_total.labels(
#             status=status,
#             method=method
#         ).inc()
    
#     def record_api_call(self, service: str, endpoint: str, status: str):
#         """Record API call metrics"""
#         self.api_calls_total.labels(
#             service=service,
#             endpoint=endpoint,
#             status=status
#         ).inc()
    
#     def record_error(self, error_type: str, source: str, severity: str = 'error'):
#         """Record error metrics"""
#         self.errors_total.labels(
#             type=error_type,
#             source=source,
#             severity=severity
#         ).inc()
    
#     # ============ PERFORMANCE METRICS ============
    
#     def update_memory_usage(self):
#         """Update memory usage metrics"""
#         import psutil
#         import os
        
#         process = psutil.Process(os.getpid())
        
#         # RSS (Resident Set Size)
#         self.memory_usage.labels(type='rss').set(process.memory_info().rss)
        
#         # VMS (Virtual Memory Size)
#         self.memory_usage.labels(type='vms').set(process.memory_info().vms)
        
#         # Shared memory
#         self.memory_usage.labels(type='shared').set(process.memory_info().shared)
    
#     def update_cpu_usage(self):
#         """Update CPU usage metrics"""
#         import psutil
#         self.cpu_usage.set(psutil.cpu_percent(interval=None))
    
#     # ============ METRICS EXPORT ============
    
#     @staticmethod
#     def metrics_view(request):
#         """Django view for Prometheus metrics endpoint"""
#         registry = MetricsRegistry().registry
#         data = generate_latest(registry)
#         return HttpResponse(data, content_type=CONTENT_TYPE_LATEST)
    
#     # ============ METRICS SERVER ============
    
#     @staticmethod
#     def start_metrics_server(port: int = 9090):
#         """Start Prometheus metrics server"""
#         try:
#             start_http_server(port)
#             logger.info(f"Prometheus metrics server started on port {port}")
#         except Exception as e:
#             logger.error(f"Failed to start metrics server: {e}")

# # ============ METRICS DECORATORS ============

# def measure_operation(operation: str, labels: Dict[str, str] = None):
#     """Decorator to measure operation duration and count"""
#     def decorator(func):
#         def wrapper(*args, **kwargs):
#             registry = MetricsRegistry()
            
#             # Create metrics if they don't exist
#             if not hasattr(registry, f'{operation}_duration'):
#                 setattr(registry, f'{operation}_duration',
#                     Histogram(
#                         f'{operation}_duration_seconds',
#                         f'Duration of {operation} operation',
#                         list(labels.keys()) if labels else [],
#                         registry=registry.registry
#                     )
#                 )
            
#             if not hasattr(registry, f'{operation}_total'):
#                 setattr(registry, f'{operation}_total',
#                     Counter(
#                         f'{operation}_total',
#                         f'Total {operation} operations',
#                         list(labels.keys()) if labels else [],
#                         registry=registry.registry
#                     )
#                 )
            
#             # Measure duration
#             start_time = time.time()
#             try:
#                 result = func(*args, **kwargs)
                
#                 # Record success
#                 duration = time.time() - start_time
#                 if labels:
#                     getattr(registry, f'{operation}_duration').labels(**labels).observe(duration)
#                     getattr(registry, f'{operation}_total').labels(**labels).inc()
#                 else:
#                     getattr(registry, f'{operation}_duration').observe(duration)
#                     getattr(registry, f'{operation}_total').inc()
                
#                 return result
                
#             except Exception as e:
#                 # Record error
#                 registry.record_error(
#                     error_type=type(e).__name__,
#                     source=operation,
#                     severity='error'
#                 )
#                 raise
        
#         return wrapper
#     return decorator

# def count_calls(metric_name: str, labels: Dict[str, str] = None):
#     """Decorator to count function calls"""
#     def decorator(func):
#         def wrapper(*args, **kwargs):
#             registry = MetricsRegistry()
            
#             # Create counter if it doesn't exist
#             if not hasattr(registry, metric_name):
#                 setattr(registry, metric_name,
#                     Counter(
#                         metric_name,
#                         f'Total calls to {metric_name}',
#                         list(labels.keys()) if labels else [],
#                         registry=registry.registry
#                     )
#                 )
            
#             # Increment counter
#             if labels:
#                 getattr(registry, metric_name).labels(**labels).inc()
#             else:
#                 getattr(registry, metric_name).inc()
            
#             return func(*args, **kwargs)
        
#         return wrapper
#     return decorator

# # ============ METRICS MANAGER ============

# class MetricsManager:
#     """Manager for application metrics"""
    
#     @staticmethod
#     def get_metrics_summary() -> Dict[str, Any]:
#         """Get summary of all metrics"""
#         registry = MetricsRegistry().registry
        
#         summary = {
#             'timestamp': datetime.now().isoformat(),
#             'metrics': {}
#         }
        
#         # Collect sample values
#         for metric in registry.collect():
#             metric_name = metric.name
#             metric_type = metric.type
            
#             samples = []
#             for sample in metric.samples:
#                 samples.append({
#                     'labels': sample.labels,
#                     'value': sample.value,
#                     'timestamp': sample.timestamp
#                 })
            
#             summary['metrics'][metric_name] = {
#                 'type': metric_type,
#                 'help': metric.documentation,
#                 'samples': samples
#             }
        
#         return summary
    
#     @staticmethod
#     def export_metrics(format: str = 'prometheus') -> str:
#         """Export metrics in specified format"""
#         registry = MetricsRegistry().registry
        
#         if format == 'prometheus':
#             return generate_latest(registry).decode('utf-8')
#         elif format == 'json':
#             import json
#             return json.dumps(MetricsManager.get_metrics_summary(), indent=2)
#         else:
#             raise ValueError(f"Unsupported format: {format}")

# # Global registry instance
# registry = MetricsRegistry()