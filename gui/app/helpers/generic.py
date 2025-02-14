from main import socketio
        
def broadcast_event(event_name):
    """
    Decorator that automatically emits a WebSocket event with the return value
    of the wrapped function.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result is not None:
                socketio.emit(event_name, result)
            return result
        return wrapper
    return decorator
