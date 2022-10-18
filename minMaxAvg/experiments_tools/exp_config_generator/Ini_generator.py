import json
import os
name = 'teste2'
base = {'enviroment': 'HopperBulletEnv-v0',
        'maxmsteps': [27, 32, 23], 'steps': [1, 2, 3]}


class Ini_Generator():
    def __init__(self, dic_list, exp_path=None, filename='ini_all.json'):
        self.__dic_list = dic_list
        self.filename = filename

        if exp_path:
            self.dir = os.path.abspath(exp_path)
            os.mkdir(exp_path)
        else:
            self.dir = os.getcwd()

    def search_existent_exp(self, dic):
        with open(self.filename) as data:
            self.__ini_data = json.load(data)
            self.__default_params = self.__ini_data[0]
            self.__base = tuple(self.__default_params['BaseEnv'].values())

        while True:
            was_found = self.search_exp(dic)
            if was_found:
                self.__env_data = self.__default_params
                break
            self.exp = input("your experiment don't exists")
            self.exp = self.exp.strip()

    def search_exp(self, dic):

        for exp in self.__ini_data:
            if dic['enviroment'] in exp.keys():
                for dics in exp[dic['enviroment']].values():
                    for key in dics:
                        for dic in self.__base:
                            if key in dic:
                                dic[key] = dics[key]

                return True

        return False

    def dic_for_inifile(self, dic):
        data = self.__env_data['BaseEnv']
        for env, values in data.items():
            for key in dic:
                if key in values:
                    values[key] = dic[key]
        self.ini_dic = data
        return data

    def create_dir(self, Name, N=0):
        directory = os.listdir(self.dir)
        dir_name = Name + '-' + str(N)
        if dir_name in directory:
            return self.create_dir(Name, N+1)
        else:
            dir_name = os.path.join(self.dir, dir_name)
            os.mkdir(dir_name)
            return dir_name

    def create_ini(self, dic):
        exp = dic['enviroment']
        folder = self.create_dir(exp)

        ini_name = os.path.basename(folder) + f'.ini'
        path = os.path.join(folder, ini_name)
        with open(path+'.txt', 'w') as params:
            params.write(ini_name+'\n')
            params.write((str(dic)))

        with open(path, 'w') as inifile:
            inifile.write('[EXP]\n')
            inifile.write('environment ='+exp+str('\n'))
            for key, args in self.ini_dic.items():
                inifile.write(key+"\n")
                for skey, sargs in args.items():
                    linha = skey+" = "+str(sargs)+"\n"
                    inifile.write(linha)
            self.create_txt(folder, ini_name)
        return ini_name

    def create_txt(self, folder, name):
        txt = open('ini_list.txt', 'a')
        txt.write(f'{folder},{name},\n')
        txt.close()

    def create_all_exp(self):
        for x in self.__dic_list:
            self.search_existent_exp(x)
            self.dic_for_inifile(x)
            self.create_ini(x)


if __name__ == '__main__':
    arquivo = GeraIni()
