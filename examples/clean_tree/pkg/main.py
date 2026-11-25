# -*- coding: utf-8 -*-
from . import app


def main():
    app.on_start_pipeline()
    return app.build() + str(app.helper_used())
