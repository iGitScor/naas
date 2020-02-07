#!/usr/bin/python
# coding: utf-8
import locale
import os
import sys

from dispatcher import create_app

# Setting locale for date conversions
if sys.platform.lower().startswith('linux'):
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
elif sys.platform.lower().startswith('win'):
    locale.setlocale(locale.LC_TIME, 'fr-FR')
else:
    locale.setlocale(locale.LC_TIME, 'fr_FR')

app = create_app()

if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0", debug=True)
