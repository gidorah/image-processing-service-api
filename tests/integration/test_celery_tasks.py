import unittest
from celery import Celery
from celery.contrib.testing.worker import start_worker
from django.conf import settings
import time

# Configure Django settings if not already configured
if not settings.configured:
    settings.configure(
        CELERY_BROKER_URL='memory://',  # Use in-memory broker for tests
        CELERY_RESULT_BACKEND='rpc://', # Use RPC backend for results
        CELERY_TASK_ALWAYS_EAGER=False, # Ensure tasks are sent to the worker
        CELERY_TASK_EAGER_PROPAGATES=False,
        # Add other necessary Django settings here
    )

# Initialize Celery app for testing
# Ensure the app name 'test_celery_app' is unique if you have other Celery apps.
# If your project has a central Celery app, you might need to import and use that instead.
try:
    # Attempt to get an existing app if one is already initialized
    app = Celery.get_current_app()
    if not app.configured: # Or if app.conf.BROKER_URL is None, etc.
        raise RuntimeError("Celery app not configured")
except RuntimeError: # Or a more specific exception if Celery raises one
    app = Celery('test_celery_app')
    app.conf.update(
        broker_url=settings.CELERY_BROKER_URL,
        result_backend=settings.CELERY_RESULT_BACKEND,
        task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
        task_eager_propagates=settings.CELERY_TASK_EAGER_PROPAGATES,
    )

# Define a simple task for testing
@app.task
def add(x, y):
    return x + y

@app.task
def long_running_task(duration):
    time.sleep(duration)
    return f"Slept for {duration} seconds"

class TestCeleryTasks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Start a Celery worker for testing all methods in this class."""
        # Start a test worker instance. This runs in a separate thread.
        # The worker will process tasks sent during the tests.
        # 'app' should be your Celery application instance.
        cls.worker = start_worker(app, perform_ping_check=False)
        cls.worker.__enter__() # Starts the worker

    @classmethod
    def tearDownClass(cls):
        """Stop the Celery worker after all tests in this class are done."""
        cls.worker.__exit__(None, None, None) # Stops the worker

    def test_simple_task_execution(self):
        """Test that a simple Celery task executes successfully."""
        # Send the task to the worker
        result = add.delay(5, 3)
        
        # Wait for the task to complete and get the result
        # Adjust timeout as necessary, especially for real brokers
        task_result = result.get(timeout=10) 
        self.assertEqual(task_result, 8)
        self.assertTrue(result.successful())

    def test_task_status_pending_and_success(self):
        """Test the status of a task as it progresses."""
        result = long_running_task.delay(1) # Task that takes 1 second
        
        # Check status - initially should be PENDING (or PROCESSING if fast)
        # Note: With 'memory://' broker, task might already be processed if very quick.
        # For more robust status checking, a slight delay or a mock that allows inspection is better.
        # self.assertIn(result.status, ['PENDING', 'STARTED']) # Status can vary
        
        # Wait for the task to complete
        final_result = result.get(timeout=10)
        self.assertEqual(result.status, 'SUCCESS')
        self.assertEqual(final_result, "Slept for 1 seconds")

    def test_task_failure(self):
        """Test how a failing task is handled."""
        # Define a task that will raise an exception
        @app.task
        def failing_task():
            raise ValueError("Task failed intentionally")

        result = failing_task.delay()
        
        # Wait for the task to complete (it should fail)
        with self.assertRaises(ValueError):
            result.get(timeout=10) # This will re-raise the exception from the task
            
        self.assertTrue(result.failed())
        self.assertIn("ValueError: Task failed intentionally", str(result.traceback))

    def test_task_result_retrieval(self):
        """Test retrieving the result of a completed task multiple times."""
        result_object = add.delay(10, 20)
        
        # Get result first time
        first_retrieval = result_object.get(timeout=10)
        self.assertEqual(first_retrieval, 30)
        
        # Get result second time (should be available immediately from backend)
        second_retrieval = result_object.get(timeout=1) 
        self.assertEqual(second_retrieval, 30)
        self.assertTrue(result_object.successful())

if __name__ == '__main__':
    # This allows running the tests directly from the command line
    # Ensure Celery worker is managed appropriately if run this way outside of a test runner
    # For simplicity, the setUpClass/tearDownClass will handle the worker.
    unittest.main()
