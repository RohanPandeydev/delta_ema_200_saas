
# ============================================
# FILE: orchestrator/services/tasks.py
# ============================================
"""
Celery tasks for async operations
"""
from orchestrator.extensions import celery
from orchestrator.services.docker_manager import docker_manager

@celery.task(name='spawn_container_task')
def spawn_container_task(user_id, credential_id):
    """Async task to spawn container"""
    return docker_manager.spawn_user_container(user_id, credential_id)

@celery.task(name='stop_container_task')
def stop_container_task(container_id):
    """Async task to stop container"""
    return docker_manager.stop_user_container(container_id)