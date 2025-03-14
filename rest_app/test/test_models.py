from django.test import TestCase
from rest_app.models import *

# Create your model tests here
class SampleModelTest(TestCase):
    def setUp(self):
        # Setup test data
        pass
        
    def test_sample(self):
        # Sample test case
        self.assertEqual(1, 1) 