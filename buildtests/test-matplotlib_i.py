#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy
from matplotlib import mlab
from matplotlib import pyplot


def main():
    # Part of the example at 
    # http://matplotlib.sourceforge.net/plot_directive/mpl_examples/pylab_examples/contour_demo.py
    delta = 0.025
    x = numpy.arange(-3.0, 3.0, delta)
    y = numpy.arange(-2.0, 2.0, delta)
    X, Y = numpy.meshgrid(x, y)
    Z1 = mlab.bivariate_normal(X, Y, 1.0, 1.0, 0.0, 0.0)
    Z2 = mlab.bivariate_normal(X, Y, 1.5, 0.5, 1, 1)
    Z = 10.0 * (Z2 - Z1)
    pyplot.figure()
    CS = pyplot.contour(X, Y, Z)
    pyplot.show()


if __name__ == "__main__":
    main()
