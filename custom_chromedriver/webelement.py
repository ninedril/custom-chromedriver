"""
WebElementクラスのラッパークラス
"""
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException

from .sleeper import Sleeper


class CustomWebElement:
    def __init__(self, element):
        """
        Parameters
        -----------
        element: WebElement
        """
        self.el = element

    def __getattr__(self, name):
        return getattr(self.el, name)

    def click(self):
        try:
            self.el.click()
        except ElementClickInterceptedException:
            self.el._parent.execute_script("arguments[0].click();", self.el)
        
        Sleeper.sleep_after_page_operation()

    def send_keys(self, *args):
        self.el.send_keys(*args)
        Sleeper.sleep_after_page_operation()

    def resend_keys(self, *args):
        """
        要素の入力文字列を消去後，再入力する
        """
        self.send_keys(Keys.CONTROL, "a")
        self.send_keys(Keys.BACK_SPACE)
        self.send_keys(*args)
        return
