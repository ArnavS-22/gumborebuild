# SQLAlchemy Transaction Context Fix

## Problem Summary

The application was experiencing SQLAlchemy transaction context errors:
```
sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction inside context manager. 
Please complete the context manager before emitting further commands.
```

## Root Cause

The issue occurred because background async tasks were trying to use database sessions after the parent transaction context had already closed. Specifically:

1. `_default_handler` method used a session context manager (`async with self._session()`)
2. Background tasks were created using `asyncio.create_task()` and passed the same session
3. When the main handler completed, the transaction closed
4. Background tasks continued running and tried to use the closed session
5. SQLAlchemy threw the transaction context error

## Production-Grade Solution

### 1. Session Isolation
- **Before**: Background tasks shared the parent session
- **After**: Each background task creates its own isolated session

### 2. Fixed Methods

#### `_trigger_proactive_suggestions(observation_id: int)`
- Removed `session: AsyncSession` parameter
- Creates own session: `async with self._session() as proactive_session:`
- Added comprehensive error handling and performance logging

#### `_trigger_gumbo_suggestions(proposition_id: int)` 
- New method that wraps the gumbo engine call
- Creates own session: `async with self._session() as gumbo_session:`
- Added comprehensive error handling and performance logging

### 3. Task Management Improvements

#### Proper Task Lifecycle Management
```python
# Before
asyncio.create_task(self._trigger_proactive_suggestions(observation.id, session))

# After  
task = asyncio.create_task(self._trigger_proactive_suggestions(observation.id))
self._tasks.add(task)
task.add_done_callback(self._tasks.discard)
```

#### Benefits:
- Prevents memory leaks from orphaned tasks
- Enables proper task cleanup on shutdown
- Provides task tracking for debugging

### 4. Enhanced Error Handling

#### Production-Grade Logging
- Added execution timing for performance monitoring
- Added debug-level start messages
- Enhanced error messages with execution context
- Added `exc_info=True` for full stack traces

#### Example:
```python
start_time = datetime.now(timezone.utc)
try:
    # ... processing ...
    processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
    self.logger.info(f"✅ Completed processing in {processing_time:.2f}s")
except Exception as e:
    processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
    self.logger.error(f"Error after {processing_time:.2f}s: {e}", exc_info=True)
```

## Files Modified

### `/gum/gum.py`
- Fixed `_default_handler` method to not pass sessions to background tasks
- Added `_trigger_gumbo_suggestions` method with proper session management
- Enhanced `_trigger_proactive_suggestions` with better error handling
- Improved task lifecycle management with proper cleanup

## Verification

### Test Script: `test_transaction_fix.py`
- Creates isolated test environment
- Simulates the conditions that caused the original error
- Verifies no SQLAlchemy transaction errors occur
- Includes proper cleanup and error reporting

### Expected Behavior After Fix
1. ✅ No more "Can't operate on closed transaction" errors
2. ✅ Background suggestion tasks run independently 
3. ✅ Proper error handling and logging for debugging
4. ✅ No memory leaks from orphaned tasks
5. ✅ Performance monitoring for background operations

## Impact Assessment

### Risk: **Low**
- Changes are isolated to background task management
- Core observation processing flow unchanged
- Backward compatible - no API changes

### Benefits: **High**
- Eliminates silent failures in suggestion systems
- Improves system reliability and observability
- Enables proper monitoring of background operations
- Prevents resource leaks

## Production Deployment Notes

1. **Monitoring**: Watch logs for the new timing information to verify background tasks are completing successfully
2. **Performance**: Background tasks now run in true isolation, which may slightly increase database connection usage but improves reliability
3. **Debugging**: Enhanced error logging will provide better diagnostics if issues occur

This fix follows production-grade patterns for async task management and database session handling in SQLAlchemy applications.
