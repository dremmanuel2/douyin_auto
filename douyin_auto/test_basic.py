# Test script for douyin-auto
import sys
sys.path.insert(0, 'e:/AI/ZJU_BJ/wxauto')

from douyin_auto import Douyin
import time

def test_basic():
    """Test basic functionality"""
    print('Testing douyin-auto...')

    try:
        # Initialize
        print('1. Creating Douyin instance...')
        dy = Douyin()
        print('   Success! Window: ' + str(dy))

        # Test window properties
        print('2. Testing window properties...')
        print('   HWND: ' + str(dy.hwnd))
        print('   Size: ' + str(dy.width) + 'x' + str(dy.height))

        # Test screenshot
        print('3. Taking screenshot...')
        path = dy.TakeScreenshot()
        print('   Screenshot saved to: ' + path)

        # Test navigation
        print('4. Testing video navigation...')
        print('   (Pressing DOWN arrow)')
        dy.NextVideo()
        time.sleep(1)
        print('   (Pressing UP arrow)')
        dy.PreviousVideo()
        time.sleep(1)
        print('   Navigation OK')

        # Test like button
        print('5. Testing Like button...')
        dy.Like()
        time.sleep(0.5)
        print('   Like OK')

        # Test comment button
        print('6. Testing OpenComments...')
        dy.OpenComments()
        time.sleep(0.5)
        dy.CloseComments()
        print('   Comments OK')

        print('')
        print('All basic tests passed!')

    except Exception as e:
        print('Error: ' + str(e))
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_basic()
