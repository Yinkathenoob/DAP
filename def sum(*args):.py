def sumo(*args):
    sum_all = 0
    for num in args:
        sum_all += num
    return sum_all


print(sumo(5, 3, 7))


