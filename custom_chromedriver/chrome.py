from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from .webelement import CustomWebElement
from .sleeper import Sleeper

from tempfile import TemporaryDirectory
import signal
import shutil
import os
import time
import logging


class CustomChrome(Chrome):
    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        logger: logging.Logger

        """
        ''' プロパティ '''
        # logger
        self.logger = kwargs.pop('logger', logging.getLogger(__name__))
        self.__common_load_timeout = 10  # サイト-サーバー間の通信時間の最大値。サイトによって調整する。

        ''' chromeオプション設定 '''
        chrome_options = kwargs.get('chrome_options', ChromeOptions())
        # 実行ファイル
        binary_location = kwargs.pop('binary_location', '')
        if binary_location:
            chrome_options.binary_location = binary_location
        # ユーザーディレクトリ
        user_data_dir = kwargs.pop('user_data_dir', '')
        if user_data_dir:
            chrome_options.add_argument('--user-data-dir={0}'.format(user_data_dir))
        ### prefs
        # ダウンロードディレクトリを追加
        self._download_dir = TemporaryDirectory()
        prefs = chrome_options.experimental_options.get("prefs", {})
        prefs.update({"download.default_directory": self._download_dir.name})
        # ページ復元ポップアップを非表示に
        prefs.update({"profile": {"exit_type": "Normal"}})
        # 反映
        chrome_options.add_experimental_option("prefs", prefs)
        # 不要なログ出力を消す
        chrome_options.add_argument('--log-level=3')
        # ウインドウサイズ
        # chrome_options.add_argument("window-size=1400,900")
        # WebDriver検出対策
        self.add_prevent_detection(chrome_options)

        ### オブジェクトを更新
        kwargs.update({'chrome_options': chrome_options})
        
        ####################### 後処理 #######################
        # Ctrl+C押下時は一時ディレクトリ削除
        signal.signal(signal.SIGTERM, lambda no, sf: self._download_dir.cleanup())
        
        super().__init__(*args, **kwargs)

        # ウインドウサイズ最大化
        self.maximize_window()
    
    @property
    def common_load_timeout(self):
        return self.__common_load_timeout

    @common_load_timeout.setter
    def common_load_timeout(self, value):
        self.__common_load_timeout = int(value)

    @staticmethod
    def add_prevent_detection(options):
        """
        WebDriver検出を回避するChromeオプションを設定する

        Parameters
        ----------
        opiton: ChromeOptions

        Returns
        ----------
        opiton: ChromeOptions
        """
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        return options

    def prepare_downloading(self):
        """ ダウンロード準備 """
        # ダウンロードディレクトリの中身を一旦消去
        download_dir = self._download_dir.name
        shutil.rmtree(download_dir)
        os.makedirs(download_dir)
        return

    def get_downloaded_file(self):
        """
        ダウンロード終了まで待機後、取得できたファイルのパスを返却
        タイムアウトを超えてもDLできなかったら空文字列を返却する
        """
        timeout_seconds = 180
        download_dir = self._download_dir.name
        for _ in range(timeout_seconds):
            time.sleep(1)
            
            download_fp = [download_dir + '\\' + e for e in os.listdir(download_dir)]
            if not download_fp:
                continue
            
            download_fp = download_fp[0]
            if download_fp.endswith('.crdownload') or download_fp.endswith('.tmp'):
                continue
            else:
                break
        else:
            self.logger.error("ファイルのダウンロード時間がタイムアウトしました。", exc_info=True)
            download_fp = ''

        return download_fp

    def download_file(self, locator, find_link_timeout=None):
        """
        ファイルをダウンロードする。
        一度につき一個しかダウンロードできないので注意。

        Parameters
        ----------
        locator: (str, str)
            ロケーター(Byオブジェクト内の定数, セレクタ文字列)
        timeout: int | None
            出現を待機する待ち時間の最大値（秒）

        Return
        ----------
        dl_fp: str
            ダウンロードされたファイルのパス
        """
        find_link_timeout = find_link_timeout or self.common_load_timeout
        dl_fp = ''
        try:
            for _ in range(3):
                self.prepare_downloading()
                # ダウンロードボタンをクリック
                self.find_clickable(locator, timeout=find_link_timeout).click()
                dl_fp = self.get_downloaded_file()
                if dl_fp:
                    break
        except Exception:
            self.logger.error("ファイルをダウンロードできませんでした。", exc_info=True)
            dl_fp = ''

        return dl_fp

    def find_visible(self, locator):
        """
        @deprecated
        表示されている要素のみ取得する
        
        Returns
        ----------
        elms: [CustomWebElement, ...]
        """
        elms = self.find_elements(*locator)
        elms = filter(lambda e: e.is_displayed(), elms)
        elms = [CustomWebElement(e) for e in elms]
        return elms

    def find_clickable(self, locator, timeout=None):
        """
        クリック可能な要素を取得する。

        Parameters
        ----------
        locator: (str, str)
            要素を特定するロケータ―。
        timeout: int | None
            出現を待機する待ち時間の最大値（秒）

        Returns
        ----------
        elm: CustomWebElement

        Raises
        ----------
        TimeoutException
            指定時間内に要素が出現しなかった場合
        """
        timeout = timeout or self.common_load_timeout
        # 表示されていてクリック可能な要素を待機する
        elm = CustomWebElement(
            WebDriverWait(self, timeout).until(
                lambda drv: list(filter(lambda el: el.is_displayed() and el.is_enabled(), drv.find_elements(*locator)))
            )[0]
        )
        return elm

    def find_clickable_no_exc(self, locator, timeout=None):
        """
        クリック可能な要素を取得する(例外発生なし)。
        見つからなければNoneを返す。

        Returns
        ----------
        elm: CustomWebElement | None
        """
        try:
            return self.find_clickable(locator, timeout=timeout)
        except TimeoutException:
            return None

    def select_by_value(self, locator, value, timeout=None):
        """ selectタグのオプションを設定する """
        select_obj = Select(self.find_clickable(locator, timeout=timeout))
        select_obj.select_by_value(value)
        self.sleep_after_page_operation()

    def sleep_after_page_operation(self):
        Sleeper.sleep_after_page_operation()

    def quit(self):
        super().quit()
        self._download_dir.cleanup()  # 一時ディレクトリ削除


