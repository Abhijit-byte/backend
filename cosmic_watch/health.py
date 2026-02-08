"""
Health check endpoints for monitoring.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache


def health_check(request):
    """
    Health check endpoint for monitoring systems.
    Returns 200 if all systems operational, 500 if any component fails.
    """
    health_status = {
        'status': 'healthy',
        'database': 'unknown',
        'cache': 'unknown',
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health_status['database'] = 'connected'
    except Exception as e:
        health_status['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check cache/Redis
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health_status['cache'] = 'connected'
        else:
            health_status['cache'] = 'error: cache not working'
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['cache'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 500
    return JsonResponse(health_status, status=status_code)
