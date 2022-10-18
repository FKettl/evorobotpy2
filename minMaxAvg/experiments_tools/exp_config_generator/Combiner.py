

class Combiner():
    def __init__(self):
        self.all_combinations = []
        self.temp_list = []

    def combine_dict_to_array(self, dict_keys_list, dict, n=0):
        if n == 0:
            self.temp_list = []
        if n == len(dict_keys_list):
            return self.all_combinations
        else:
            for x in dict[dict_keys_list[n]]:
                self.temp_list.append(x)
                if n == len(dict_keys_list)-1:
                    self.all_combinations.append(self.temp_list.copy())
                self.combine_dict_to_array(dict_keys_list, dict, n+1)
                self.temp_list.pop()

    def array_to_dict(self, dict_keys_list):
        new_dic = {}
        new_list = []
        for lista in self.all_combinations:
            for x in range(len(dict_keys_list)):
                new_dic[dict_keys_list[x]] = lista[x]

            new_list.append(new_dic.copy())
        self.all_combinations = new_list


if __name__ == '__main__':
    d = Combiner()
    base = {'enviroment': ['HopperBulletEnv-v0', 'Walker2DBulletEnv-v5'],
            'maxmsteps': [27, 32, 23]}
    dic_keys = list(base.keys())

    bat = d.combine_dict_to_array(dic_keys, base)
    print(d.all_combinations)
    d.array_to_dict(dic_keys)
# print(d.combinados)

    gerador = GeraIni(d.all_combinations)
    gerador.criar_all_exp()
