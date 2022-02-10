"""
コードを一時停止する役割を持つクラス
"""
import time
import random


class Sleeper:
    @staticmethod
    def sleep_after_page_operation():
        """
        クリック等のユーザーによるページ操作後に，一定時間スリープする
        """
        i = 1 + random.expovariate(1.2)
        time.sleep(i)
