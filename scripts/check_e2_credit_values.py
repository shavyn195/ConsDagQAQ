"""Hand-calculated credit: successful compliant/violating pair with one bound tool."""
from e2_credit import advantages
from math import isclose

def main():
    group = [dict(done=True,bad=[],loc={}),dict(done=True,bad=[0],loc={0:1})]
    expected = {"trace":[-1.]*4, "action":[0.,-4.,0.,0.], "shifted":[0.,0.,0.,-4.]}
    for arm, want in expected.items():
        rewards, vals, moved = advantages(group,[4,4],[{}, {1:[1]}],1,arm)
        assert rewards == [2.,1.] and vals[0]==[1.]*4 and vals[1]==want and moved==int(arm!="trace")
    for arm in ("function","trace","action","shifted"):
        _,vs,_ = advantages([group[1]]*2,[4,4],[{1:[1]}]*2,1,arm)
        assert all(isclose(x,0.) for row in vs for x in row)
    print("credit arithmetic passed")

if __name__=="__main__":
    main()
