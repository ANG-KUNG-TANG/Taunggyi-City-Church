# """
# Production Tracing System with OpenTelemetry
# Features:
# - Distributed tracing
# - Performance profiling
# - Span context propagation
# - Correlation IDs
# - Integration with metrics
# """

# import time
# import logging
# import contextvars
# import uuid
# from typing import Dict, Any, Optional, List, Callable
# from contextlib import contextmanager
# from dataclasses import dataclass, field
# from enum import Enum
# from datetime import datetime
# from functools import wraps

# from opentelemetry import trace
# from opentelemetry.trace import (
#     Status, StatusCode, Span, Tracer, 
#     SpanKind, set_span_in_context
# )
# from opentelemetry.context import Context
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import (
#     BatchSpanProcessor,
#     ConsoleSpanExporter,
#     SimpleSpanProcessor
# )
# from opentelemetry.exporter.jaeger.thrift import JaegerExporter
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# from opentelemetry.sdk.resources import Resource
# from opentelemetry.instrumentation.django import DjangoInstrumentor
# from opentelemetry.instrumentation.requests import RequestsInstrumentor
# from opentelemetry.instrumentation.redis import RedisInstrumentor
# from opentelemetry.instrumentation.dbapi import trace_integration
# from django.conf import settings
# import requests

# logger = logging.getLogger(__name__)

# # ============ TRACING CONFIGURATION ============

# class TracingConfig:
#     """Configuration for tracing system"""
    
#     # Exporters
#     ENABLED = getattr(settings, 'TRACING_ENABLED', True)
#     EXPORTER = getattr(settings, 'TRACING_EXPORTER', 'console')  # console, jaeger, otlp
#     SERVICE_NAME = getattr(settings, 'SERVICE_NAME', 'django-app')
#     SERVICE_VERSION = getattr(settings, 'SERVICE_VERSION', '1.0.0')
    
#     # Jaeger configuration
#     JAEGER_HOST = getattr(settings, 'JAEGER_HOST', 'localhost')
#     JAEGER_PORT = getattr(settings, 'JAEGER_PORT', 6831)
    
#     # OTLP configuration
#     OTLP_ENDPOINT = getattr(settings, 'OTLP_ENDPOINT', 'http://localhost:4317')
    
#     # Sampling rate (0.0 to 1.0)
#     SAMPLING_RATE = getattr(settings, 'TRACING_SAMPLING_RATE', 0.1)
    
#     # Batch configuration
#     BATCH_MAX_SIZE = getattr(settings, 'TRACING_BATCH_SIZE', 512)
#     BATCH_TIMEOUT = getattr(settings, 'TRACING_BATCH_TIMEOUT', 5)  # seconds
    
#     # Attributes
#     ATTRIBUTES = {
#         'service.name': SERVICE_NAME,
#         'service.version': SERVICE_VERSION,
#         'deployment.environment': getattr(settings, 'ENVIRONMENT', 'development')
#     }

# # ============ TRACING SETUP ============

# class TracingSystem:
#     """Central tracing system for the application"""
    
#     _instance = None
#     _tracer_provider = None
#     _tracer = None
#     _initialized = False
    
#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#         return cls._instance
    
#     def initialize(self):
#         """Initialize tracing system"""
#         if self._initialized:
#             return
        
#         if not TracingConfig.ENABLED:
#             logger.info("Tracing is disabled")
#             return
        
#         try:
#             # Create resource
#             resource = Resource(attributes=TracingConfig.ATTRIBUTES)
            
#             # Create tracer provider
#             self._tracer_provider = TracerProvider(resource=resource)
            
#             # Configure exporter
#             exporter = self._create_exporter()
            
#             # Create span processor
#             span_processor = BatchSpanProcessor(
#                 exporter,
#                 max_export_batch_size=TracingConfig.BATCH_MAX_SIZE,
#                 schedule_delay_millis=TracingConfig.BATCH_TIMEOUT * 1000
#             )
            
#             self._tracer_provider.add_span_processor(span_processor)
            
#             # Set global tracer provider
#             trace.set_tracer_provider(self._tracer_provider)
            
#             # Create tracer
#             self._tracer = trace.get_tracer(
#                 TracingConfig.SERVICE_NAME,
#                 TracingConfig.SERVICE_VERSION
#             )
            
#             # Auto-instrument Django
#             DjangoInstrumentor().instrument()
            
#             # Auto-instrument requests
#             RequestsInstrumentor().instrument()
            
#             # Auto-instrument Redis if available
#             try:
#                 RedisInstrumentor().instrument()
#             except ImportError:
#                 logger.debug("Redis instrumentation not available")
            
#             self._initialized = True
#             logger.info(f"Tracing system initialized with {TracingConfig.EXPORTER} exporter")
            
#         except Exception as e:
#             logger.error(f"Failed to initialize tracing system: {e}")
#             # Fallback to console exporter
#             self._initialize_fallback()
    
#     def _create_exporter(self):
#         """Create span exporter based on configuration"""
#         exporter_type = TracingConfig.EXPORTER.lower()
        
#         if exporter_type == 'jaeger':
#             return JaegerExporter(
#                 agent_host_name=TracingConfig.JAEGER_HOST,
#                 agent_port=TracingConfig.JAEGER_PORT,
#             )
        
#         elif exporter_type == 'otlp':
#             return OTLPSpanExporter(
#                 endpoint=TracingConfig.OTLP_ENDPOINT,
#                 insecure=True
#             )
        
#         elif exporter_type == 'console':
#             return ConsoleSpanExporter()
        
#         else:
#             logger.warning(f"Unknown exporter type: {exporter_type}, using console")
#             return ConsoleSpanExporter()
    
#     def _initialize_fallback(self):
#         """Initialize fallback tracing system"""
#         self._tracer_provider = TracerProvider()
#         console_exporter = ConsoleSpanExporter()
#         self._tracer_provider.add_span_processor(SimpleSpanProcessor(console_exporter))
#         trace.set_tracer_provider(self._tracer_provider)
#         self._tracer = trace.get_tracer(TracingConfig.SERVICE_NAME)
#         self._initialized = True
#         logger.info("Fallback tracing system initialized")
    
#     def get_tracer(self) -> Tracer:
#         """Get tracer instance"""
#         if not self._initialized:
#             self.initialize()
#         return self._tracer
    
#     def shutdown(self):
#         """Shutdown tracing system"""
#         if self._tracer_provider:
#             self._tracer_provider.force_flush()
#             self._tracer_provider.shutdown()
#             self._initialized = False
#             logger.info("Tracing system shutdown")

# # ============ TRACING CONTEXT ============

# # Context variables for propagation
# current_span = contextvars.ContextVar('current_span', default=None)
# correlation_id = contextvars.ContextVar('correlation_id', default=None)

# @dataclass
# class SpanContext:
#     """Span context for distributed tracing"""
#     trace_id: str
#     span_id: str
#     trace_flags: int = 1
#     is_remote: bool = False
    
#     @classmethod
#     def from_span(cls, span: Span) -> 'SpanContext':
#         """Create SpanContext from OpenTelemetry span"""
#         span_context = span.get_span_context()
#         return cls(
#             trace_id=format(span_context.trace_id, '032x'),
#             span_id=format(span_context.span_id, '016x'),
#             trace_flags=span_context.trace_flags,
#             is_remote=False
#         )
    
#     @classmethod
#     def from_headers(cls, headers: Dict[str, str]) -> Optional['SpanContext']:
#         """Extract SpanContext from HTTP headers"""
#         trace_id = headers.get('X-Trace-ID')
#         span_id = headers.get('X-Span-ID')
        
#         if trace_id and span_id:
#             return cls(
#                 trace_id=trace_id,
#                 span_id=span_id,
#                 trace_flags=1,
#                 is_remote=True
#             )
#         return None
    
#     def to_headers(self) -> Dict[str, str]:
#         """Convert to HTTP headers for propagation"""
#         return {
#             'X-Trace-ID': self.trace_id,
#             'X-Span-ID': self.span_id,
#             'X-Correlation-ID': get_correlation_id() or ''
#         }

# # ============ TRACING UTILITIES ============

# def start_span(
#     name: str,
#     kind: SpanKind = SpanKind.INTERNAL,
#     attributes: Dict[str, Any] = None,
#     parent_context: Optional[Context] = None
# ) -> Span:
#     """Start a new span"""
#     tracer_system = TracingSystem()
#     tracer = tracer_system.get_tracer()
    
#     if parent_context is None:
#         parent_context = trace.get_current_span().get_span_context()
    
#     span = tracer.start_span(
#         name=name,
#         kind=kind,
#         attributes=attributes or {},
#         start_time=time.time_ns(),
#         context=parent_context
#     )
    
#     # Set as current span
#     current_span.set(span)
    
#     # Generate correlation ID if not exists
#     if correlation_id.get() is None:
#         correlation_id.set(str(uuid.uuid4()))
    
#     return span

# @contextmanager
# def span(
#     name: str,
#     kind: SpanKind = SpanKind.INTERNAL,
#     attributes: Dict[str, Any] = None,
#     record_exception: bool = True
# ):
#     """Context manager for creating spans"""
#     span_obj = start_span(name, kind, attributes)
    
#     try:
#         yield span_obj
#         span_obj.set_status(Status(StatusCode.OK))
#     except Exception as e:
#         if record_exception:
#             span_obj.record_exception(e)
#             span_obj.set_status(Status(StatusCode.ERROR, str(e)))
#         raise
#     finally:
#         span_obj.end(end_time=time.time_ns())

# def get_current_span() -> Optional[Span]:
#     """Get current active span"""
#     return current_span.get()

# def set_current_span(span: Span):
#     """Set current active span"""
#     current_span.set(span)

# def get_correlation_id() -> Optional[str]:
#     """Get current correlation ID"""
#     return correlation_id.get()

# def set_correlation_id(cid: str):
#     """Set correlation ID"""
#     correlation_id.set(cid)

# def generate_correlation_id() -> str:
#     """Generate a new correlation ID"""
#     cid = str(uuid.uuid4())
#     set_correlation_id(cid)
#     return cid

# # ============ TRACING DECORATORS ============

# def traced(name: str = None, attributes: Dict[str, Any] = None):
#     """Decorator to trace function execution"""
#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             span_name = name or f"{func.__module__}.{func.__name__}"
            
#             with span(span_name, attributes=attributes) as span_obj:
#                 # Add function arguments as span attributes
#                 span_obj.set_attributes({
#                     'function.module': func.__module__,
#                     'function.name': func.__name__,
#                     'function.args.count': len(args) + len(kwargs)
#                 })
                
#                 try:
#                     result = func(*args, **kwargs)
#                     span_obj.set_attribute('function.result.type', type(result).__name__)
#                     return result
#                 except Exception as e:
#                     span_obj.record_exception(e)
#                     span_obj.set_status(Status(StatusCode.ERROR, str(e)))
#                     raise
        
#         return wrapper
#     return decorator

# def traced_async(name: str = None, attributes: Dict[str, Any] = None):
#     """Decorator to trace async function execution"""
#     def decorator(func):
#         @wraps(func)
#         async def wrapper(*args, **kwargs):
#             span_name = name or f"{func.__module__}.{func.__name__}"
            
#             with span(span_name, attributes=attributes) as span_obj:
#                 # Add function arguments as span attributes
#                 span_obj.set_attributes({
#                     'function.module': func.__module__,
#                     'function.name': func.__name__,
#                     'function.args.count': len(args) + len(kwargs),
#                     'function.async': True
#                 })
                
#                 try:
#                     result = await func(*args, **kwargs)
#                     span_obj.set_attribute('function.result.type', type(result).__name__)
#                     return result
#                 except Exception as e:
#                     span_obj.record_exception(e)
#                     span_obj.set_status(Status(StatusCode.ERROR, str(e)))
#                     raise
        
#         return wrapper
#     return decorator

# # ============ SPAN ATTRIBUTES ============

# def add_span_attribute(key: str, value: Any):
#     """Add attribute to current span"""
#     span = get_current_span()
#     if span:
#         span.set_attribute(key, value)

# def add_span_attributes(attributes: Dict[str, Any]):
#     """Add multiple attributes to current span"""
#     span = get_current_span()
#     if span:
#         for key, value in attributes.items():
#             span.set_attribute(key, value)

# def add_span_event(name: str, attributes: Dict[str, Any] = None):
#     """Add event to current span"""
#     span = get_current_span()
#     if span:
#         span.add_event(name, attributes=attributes or {})

# # ============ TRACING MIDDLEWARE ============

# class TracingMiddleware:
#     """Django middleware for distributed tracing"""
    
#     def __init__(self, get_response):
#         self.get_response = get_response
#         self.tracing_system = TracingSystem()
    
#     def __call__(self, request):
#         # Skip tracing for certain paths
#         if self._should_skip_tracing(request):
#             return self.get_response(request)
        
#         # Extract trace context from headers
#         trace_context = SpanContext.from_headers(request.headers)
        
#         # Generate correlation ID
#         cid = request.headers.get('X-Correlation-ID') or generate_correlation_id()
#         set_correlation_id(cid)
        
#         # Start span for the request
#         span_name = f"{request.method} {request.path}"
        
#         with span(
#             name=span_name,
#             kind=SpanKind.SERVER,
#             attributes=self._get_request_attributes(request)
#         ) as span_obj:
#             # Store span in request for downstream use
#             request.span = span_obj
#             request.correlation_id = cid
            
#             # Add response headers
#             response = self.get_response(request)
            
#             # Add tracing headers to response
#             self._add_tracing_headers(response, span_obj)
            
#             return response
    
#     def _should_skip_tracing(self, request) -> bool:
#         """Check if tracing should be skipped for this request"""
#         skip_paths = ['/health', '/metrics', '/favicon.ico']
#         return any(request.path.startswith(path) for path in skip_paths)
    
#     def _get_request_attributes(self, request) -> Dict[str, Any]:
#         """Extract attributes from HTTP request"""
#         return {
#             'http.method': request.method,
#             'http.url': request.build_absolute_uri(),
#             'http.route': request.path,
#             'http.user_agent': request.META.get('HTTP_USER_AGENT', ''),
#             'http.client_ip': self._get_client_ip(request),
#             'http.content_length': request.META.get('CONTENT_LENGTH', 0),
#             'http.scheme': request.scheme,
#             'correlation_id': get_correlation_id()
#         }
    
#     def _get_client_ip(self, request) -> str:
#         """Extract client IP from request"""
#         x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#         if x_forwarded_for:
#             return x_forwarded_for.split(',')[0]
#         return request.META.get('REMOTE_ADDR', 'unknown')
    
#     def _add_tracing_headers(self, response, span: Span):
#         """Add tracing headers to HTTP response"""
#         span_context = SpanContext.from_span(span)
        
#         response['X-Trace-ID'] = span_context.trace_id
#         response['X-Span-ID'] = span_context.span_id
#         response['X-Correlation-ID'] = get_correlation_id()

# # ============ TRACING FOR DATABASE ============

# class DatabaseTracing:
#     """Database query tracing"""
    
#     @staticmethod
#     @contextmanager
#     def trace_query(
#         query: str,
#         operation: str,
#         table: str = None,
#         parameters: List[Any] = None
#     ):
#         """Trace database query execution"""
#         with span(
#             name=f"db.{operation}",
#             kind=SpanKind.CLIENT,
#             attributes={
#                 'db.system': 'postgresql',
#                 'db.operation': operation,
#                 'db.statement': query,
#                 'db.table': table,
#                 'db.parameters': str(parameters) if parameters else None
#             }
#         ) as span_obj:
#             start_time = time.time()
#             try:
#                 yield span_obj
#                 duration = time.time() - start_time
#                 span_obj.set_attribute('db.duration_ms', duration * 1000)
#                 span_obj.set_status(Status(StatusCode.OK))
#             except Exception as e:
#                 duration = time.time() - start_time
#                 span_obj.set_attribute('db.duration_ms', duration * 1000)
#                 span_obj.record_exception(e)
#                 span_obj.set_status(Status(StatusCode.ERROR, str(e)))
#                 raise

# # ============ TRACING FOR CACHE ============

# class CacheTracing:
#     """Cache operation tracing"""
    
#     @staticmethod
#     @contextmanager
#     def trace_operation(
#         operation: str,
#         key: str,
#         cache_name: str = 'default'
#     ):
#         """Trace cache operation"""
#         with span(
#             name=f"cache.{operation}",
#             kind=SpanKind.CLIENT,
#             attributes={
#                 'cache.operation': operation,
#                 'cache.key': key,
#                 'cache.name': cache_name
#             }
#         ) as span_obj:
#             start_time = time.time()
#             try:
#                 yield span_obj
#                 duration = time.time() - start_time
#                 span_obj.set_attribute('cache.duration_ms', duration * 1000)
#                 span_obj.set_status(Status(StatusCode.OK))
#             except Exception as e:
#                 duration = time.time() - start_time
#                 span_obj.set_attribute('cache.duration_ms', duration * 1000)
#                 span_obj.record_exception(e)
#                 span_obj.set_status(Status(StatusCode.ERROR, str(e)))
#                 raise

# # ============ TRACING FOR EXTERNAL SERVICES ============

# class ExternalServiceTracing:
#     """Tracing for external service calls"""
    
#     @staticmethod
#     def trace_http_request(
#         method: str,
#         url: str,
#         service_name: str,
#         headers: Dict[str, str] = None
#     ) -> Dict[str, str]:
#         """Generate headers for external HTTP request tracing"""
#         current = get_current_span()
#         if not current:
#             return headers or {}
        
#         # Create span context
#         span_context = SpanContext.from_span(current)
        
#         # Add tracing headers
#         tracing_headers = span_context.to_headers()
#         tracing_headers.update({
#             'X-Service-Call': service_name,
#             'X-Caller-Service': TracingConfig.SERVICE_NAME
#         })
        
#         # Merge with existing headers
#         if headers:
#             tracing_headers.update(headers)
        
#         return tracing_headers
    
#     @staticmethod
#     @contextmanager
#     def trace_external_call(
#         service: str,
#         endpoint: str,
#         method: str = 'GET'
#     ):
#         """Trace external service call"""
#         with span(
#             name=f"external.{service}.{endpoint}",
#             kind=SpanKind.CLIENT,
#             attributes={
#                 'external.service': service,
#                 'external.endpoint': endpoint,
#                 'external.method': method
#             }
#         ) as span_obj:
#             start_time = time.time()
#             try:
#                 yield span_obj
#                 duration = time.time() - start_time
#                 span_obj.set_attribute('external.duration_ms', duration * 1000)
#                 span_obj.set_status(Status(StatusCode.OK))
#             except Exception as e:
#                 duration = time.time() - start_time
#                 span_obj.set_attribute('external.duration_ms', duration * 1000)
#                 span_obj.record_exception(e)
#                 span_obj.set_status(Status(StatusCode.ERROR, str(e)))
#                 raise

# # ============ TRACING REPORTER ============

# class TracingReporter:
#     """Reporter for tracing data"""
    
#     @staticmethod
#     def generate_trace_url(trace_id: str) -> str:
#         """Generate URL for trace visualization"""
#         if TracingConfig.EXPORTER == 'jaeger':
#             return f"http://{TracingConfig.JAEGER_HOST}:16686/trace/{trace_id}"
#         elif TracingConfig.EXPORTER == 'otlp':
#             return f"http://{TracingConfig.OTLP_ENDPOINT}/traces/{trace_id}"
#         else:
#             return f"trace://{trace_id}"
    
#     @staticmethod
#     def get_current_trace_info() -> Dict[str, Any]:
#         """Get current trace information"""
#         span = get_current_span()
#         if not span:
#             return {}
        
#         span_context = span.get_span_context()
        
#         return {
#             'trace_id': format(span_context.trace_id, '032x'),
#             'span_id': format(span_context.span_id, '016x'),
#             'trace_flags': span_context.trace_flags,
#             'is_sampled': span_context.trace_flags == 1,
#             'correlation_id': get_correlation_id(),
#             'trace_url': TracingReporter.generate_trace_url(
#                 format(span_context.trace_id, '032x')
#             )
#         }
    
#     @staticmethod
#     def log_trace_info(span_name: str, attributes: Dict[str, Any] = None):
#         """Log trace information for debugging"""
#         trace_info = TracingReporter.get_current_trace_info()
        
#         log_data = {
#             'trace_id': trace_info.get('trace_id'),
#             'span_id': trace_info.get('span_id'),
#             'correlation_id': trace_info.get('correlation_id'),
#             'span_name': span_name,
#             'attributes': attributes or {},
#             'timestamp': datetime.now().isoformat()
#         }
        
#         logger.info(
#             f"Trace: {span_name}",
#             extra={'trace': log_data}
#         )
        
#         return trace_info

# # ============ GLOBAL INSTANCES ============

# # Initialize tracing system
# tracer_system = TracingSystem()
# tracer_system.initialize()

# # Get global tracer
# tracer = tracer_system.get_tracer()

# # Global span function
# span = span

# # Global traced decorators
# traced = traced
# traced_async = traced_async