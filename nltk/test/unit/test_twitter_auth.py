# -*- coding: utf-8 -*-
"""
Tests for static parts of Twitter package
"""

import os
import unittest

from nltk.twitter import Authenticate


class TestCredentials(unittest.TestCase):
    """
    Tests that Twitter credentials information from file is handled correctly.
    """

    def setUp(self):
        self.subdir = os.path.join(os.path.dirname(__file__), 'files')
        self.auth = Authenticate()
        os.environ['TWITTER'] = 'twitter-files'

    def test_environment(self):
        """
        Test that environment variable has been read correctly.
        """
        fn = os.path.basename(self.auth.creds_subdir)
        self.assertEqual(fn, os.environ['TWITTER'])

    def test_empty_subdir1(self):
        """
        Setting subdir to empty path should raise an error.
        """
        try:
            self.auth.load_creds(subdir='')
        # raises ValueError (zero length field name in format) for python 2.6
        # OSError for the rest
        except OSError:
            pass
        except ValueError:
            pass
        except Exception as e:
            self.fail('Unexpected exception thrown: %s' % e)
        else:
            self.fail('OSError exception not thrown.')
            

    def test_empty_subdir2(self):
        """
        Setting subdir to `None` should raise an error.
        """
        self.auth.creds_subdir = None
        try:
            self.auth.load_creds()
        except ValueError:
            pass
        except Exception as e:
            self.fail('Unexpected exception thrown: %s' % e)
        else:
            self.fail('ValueError exception not thrown.')

    def test_missingdir(self):
        """
        Setting subdir to nonexistent directory should raise an error.
        """
        try:
            self.auth.load_creds(subdir='/nosuchdir')
        # raises ValueError (zero length field name in format) for python 2.6
        # OSError for the rest
        except OSError:
            pass
        except ValueError:
            pass
        except Exception as e:
            self.fail('Unexpected exception thrown: %s' % e)
        else:
            self.fail('OSError exception not thrown.')


    def test_missingfile1(self):
        """
        Defaults for authentication will fail since 'credentials.txt' not
        present in default subdir, as read from `os.environ['TWITTER']`.
        """
        try:
            self.auth.load_creds()
        # raises ValueError (zero length field name in format) for python 2.6
        # OSError for the rest
        except OSError:
            pass
        except ValueError:
            pass
        except Exception as e:
            self.fail('Unexpected exception thrown: %s' % e)
        else:
            self.fail('OSError exception not thrown.')


    def test_missingfile2(self):
        """
        Credentials file 'foobar' cannot be found in default subdir.
        """
        try:
            self.auth.load_creds(creds_file='foobar')
        # raises ValueError (zero length field name in format) for python 2.6
        # OSError for the rest
        except OSError:
            pass
        except ValueError:
            pass
        except Exception as e:
            self.fail('Unexpected exception thrown: %s' % e)
        else:
            self.fail('OSError exception not thrown.')



    def test_incomplete_file(self):
        """
        Credentials file 'bad_oauth1-1.txt' is incomplete
        """
        try:
            self.auth.load_creds(creds_file='bad_oauth1-1.txt',
                                 subdir=self.subdir)
        except ValueError:
            pass
        except Exception as e:
            self.fail('Unexpected exception thrown: %s' % e)
        else:
            self.fail('ValueError exception not thrown.')


    def test_malformed_file1(self):
        """
        First key in credentials file 'bad_oauth1-2.txt' is ill-formed
        """
        try:
            self.auth.load_creds(creds_file='bad_oauth1-2.txt',
                                 subdir=self.subdir)
        except ValueError:
            pass
        except Exception as e:
            self.fail('Unexpected exception thrown: %s' % e)
        else:
            self.fail('ValueError exception not thrown.')

    def test_malformed_file2(self):
        """
        First key in credentials file 'bad_oauth1-2.txt' is ill-formed
        """
        try:
            self.auth.load_creds(creds_file='bad_oauth1-3.txt',
                                 subdir=self.subdir)
        except ValueError:
            pass
        except Exception as e:
            self.fail('Unexpected exception thrown: %s' % e)
        else:
            self.fail('ValueError exception not thrown.')

    def test_correct_path(self):
        """
        Path to default credentials file is well-formed, given specified
        subdir.
        """
        self.auth.load_creds(subdir=self.subdir)
        self.auth.creds_fullpath = os.path.join(self.subdir, self.auth.creds_file)


    def test_correct_file1(self):
        """
        Default credentials file is identified
        """
        self.auth.load_creds(subdir=self.subdir)
        self.assertEqual(self.auth.creds_file, 'credentials.txt')


    def test_correct_file2(self):
        """
        Default credentials file has been read correctluy
        """
        oauth = self.auth.load_creds(subdir=self.subdir)
        self.assertEqual(oauth['app_key'], 'a')


if __name__ == '__main__':
    unittest.main()

