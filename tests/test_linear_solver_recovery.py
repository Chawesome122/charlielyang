"""Recover from a real Krylov failure without weakening numerical acceptance."""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from unittest.mock import patch
from weaponized.game.hjb import StateGrid, build_generator, evaluate_policies
from weaponized.game.primitives import GameParameters, payoffs


def test_gmres_fallback_matches_independent_direct_solve():
    grid=StateGrid(4);p=GameParameters()
    u=np.full(grid.count,.3);c=np.full(grid.count,.6)
    with patch("weaponized.game.hjb.bicgstab",return_value=(np.full(grid.count,np.nan),3000)):
        values,diagnostics=evaluate_policies(grid,p,u,c)
    generator=build_generator(grid,p,u,c);rewards=payoffs(grid.states,u,c,p)
    for i,rho in enumerate((p.rho_u,p.rho_c)):
        exact=spsolve(rho*sparse.eye(grid.count)-generator,rewards[i])
        assert np.max(abs(values[i]-exact))<1e-8
        assert diagnostics['players'][i]['linear_method']=='gmres_jacobi_after_bicgstab_failure'
        assert diagnostics['players'][i]['final_solver_code']==0
