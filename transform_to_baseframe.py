import numpy as np

def transform_to_baseframe(point):
    # update once L is fixed on table
    T_fromscan_tobase = np.array([[0, 1,  0, -150],
                                  [-1, 0, 0, -240],
                                  [0, 0,  1, -10],
                                  [0, 0,  0,  1]]) 
    point_with1 = np.append(point, 1)
    point_in_baseframe = np.matmul(T_fromscan_tobase, point_with1)
    return point_in_baseframe[:-1]

if __name__ == "__main__":
    test_point = np.array([[0, 100, 0]])
    print(transform_to_baseframe(test_point))