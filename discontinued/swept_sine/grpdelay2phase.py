#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
ADAPTACION DEL ORIGINAL:
https://es.mathworks.com/matlabcentral/fileexchange/29187-swept-sine-analysis

%%% grpdelay2phase.m

%%% get the phase from the group delay

function ph = grpdelay2phase(grd)

% ph = zeros(1,N);
% ph(1) = -grd(1);
% for i = 2:N
%     ph(i) = -(-ph(i-1)+grd(i));
% end
ph = -cumsum(grd);
ph = 2*pi*ph/length(grd);
"""

import numpy as np

def grpdelay2phase(grd):
    ph = -np.cumsum(grd)
    return 2 * np.pi * ph / len(grd)
