#!/usr/bin/env python3
"""
Run all tests for the PolicyEngine Social Media Automation system.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all test modules
from test_extract_blog_images import TestBlogImageExtractor, TestImageIntegration
from test_generate_social_post import (
    TestSocialPostGenerator, 
    TestContentVariations, 
    TestErrorHandling
)
from test_publish_to_x import TestXPublisher, TestPublishingSchedule


def create_test_suite():
    """Create and return a test suite with all tests."""
    suite = unittest.TestSuite()
    
    # Add image extraction tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBlogImageExtractor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestImageIntegration))
    
    # Add post generation tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSocialPostGenerator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestContentVariations))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestErrorHandling))
    
    # Add publishing tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestXPublisher))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPublishingSchedule))
    
    return suite


if __name__ == '__main__':
    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    suite = create_test_suite()
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)