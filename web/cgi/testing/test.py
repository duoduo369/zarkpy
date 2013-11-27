#!/usr/bin/env python
#coding=utf-8
''' 对testing中的测试用例进行测试，测试过程中会操作数据库与数据文件，
    因此需要新建测试专用的数据库与文件存放路径,请在运行此脚本之前检查:
    1 是否所有的文件保存路径都已加入TEST_PATH列表？
    2 以及对应的访问路径是否都已加入TEST_URL列表？
    若为否,将可能导致您本地的数据丢失 '''

TEST_PATH = ['UPLOAD_IMAGE_PATH', 'USER_IMAGE_PATH']
TEST_URL  = ['UPLOAD_IMAGE_URL', 'USER_IMAGE_URL']

assert __name__ == "__main__", u'test.py只能运行,切勿导入,以免因不小心操作导致数据丢失'
import os, re, sys

import web
web.config.debug = False

from unittest import TestLoader, TestSuite, TextTestRunner, TestCase

# 添加cgi文件夹所在路径, 以实现下面的import
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0].rpartition('/')[0])
import site_helper as sh
assert sh.config.HOST_NAME == 'http://me.zarkpy.com', u'只能在开发环境中运行测试'

# 为测试修改配置，以免改动正式数据库与正式文件
# 如果万一不小心没有把sh.config.IS_TEST改为True，就会删除正式数据
# 为了避免意外删除正式数据库，除此函数外应该不允许修改sh.config.IS_TEST
def modifyConfigForTest():
    sh.config.IS_TEST = True
    for k in TEST_PATH + TEST_URL:
        sh.config[k] = sh.config[k].rstrip('/') + '-testing/'
    sh.config.DB_DATABASE += '_test'

# 清空并重建测试数据库
def rebulidTestDataBase():
    from tool import init_database
    assert sh.config.DB_DATABASE.endswith('_test'), u'你使用正式数据库来测试?'
    db = sh.getDBHelper()
    for table_name in db.fetchSomeFirst('show tables', ignore_assert=True):
        db.executeQuery('DROP TABLE %s' % table_name)
    init_database.initTables()

# 清空测试过程中创建的以"-testing"结尾的测试文件夹
def emptyTestFileDir():
    for k in TEST_PATH:
        v = sh.config[k]
        assert v.endswith('-testing/'), u'你使用正式文件数据来测试?'
        sh.autoMkdir(v)
        # 递归删除v中的所有文件,但保留空文件夹,以免下次测试时再创建
        os.system('find "%s" -type f | xargs rm -rf' % v)

# 获得指定路径中所有Test*.py文件的完整路径
def getTestPaths(paths):
    file_names = []
    cwd = os.getcwd()
    for path in paths:
        # 把相对路径改为绝对路径
        if not path.startswith('/'):
            path = os.path.join(cwd, path)
        assert os.path.exists(path), u'输入的测试文件不存在:%s' % path
        if os.path.isdir(path):
            find_cmd = 'find "%s" -name "Test*.py"' % path.rstrip('/')
            file_names += [f for f in os.popen(find_cmd).read().split('\n') if f]
        elif os.path.isfile(path):
            file_names.append(path)
    return [os.path.abspath(f) for f in list(set(file_names))]

def pathToModuleName(paths):
    for p in paths:
        if p.split('/').count('testing') == 0:
            raise Exception('测试用例必须放到%s文件夹中' % (sh.config.APP_ROOT_PATH + 'web/cgi/testing/'))
        elif p.split('/').count('testing') != 1:
            raise Exception('testing文件夹中不能再有名为testing的文件夹')
    return [p.rpartition('/testing/')[2] for p in paths]

def mainTest():
    module_names = pathToModuleName(getTestPaths(sys.argv[1:]))
    module_names = ['testing.%s' % f.rpartition('.py')[0].replace('/', '.') for f in module_names]
    suites = []
    for module_name in module_names:
        if '.' in module_name:
            exec('from %s import %s as test_module' % module_name.rpartition('.')[::2])
        else:
            exec('import %s as test_module' % module_name)
        class_name = module_name.rpartition('.')[2]
        test_class = eval("test_module.%s" % class_name)
        assert issubclass(test_class, TestCase), u'仅能对unittest.TestCase的子类进行测试,忘记继承它了?'
        suites.append( TestLoader().loadTestsFromTestCase(test_class) )
    TextTestRunner().run( TestSuite(suites) )

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print 'Usage:'
        print '    python test.py [FILE] [FILE] ...'
        print '    FILE可以是测试文件名，也可以是文件夹'
        print '    如果是文件夹，则将自动查找里面的Test*.py文件'
    else:
        modifyConfigForTest()
        rebulidTestDataBase()
        emptyTestFileDir()
        mainTest()
