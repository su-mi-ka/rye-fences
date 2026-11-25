# -*- coding: utf-8 -*-
from . import app


def main():
    # on_start_pipeline() も helper_unused() も、ここでは呼ばれない。
    return app.build()
