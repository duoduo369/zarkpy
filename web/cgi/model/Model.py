#coding=utf-8
import web
import re
import DBHelper
import site_helper as sh

# model模块的基类
# 子类的calss名称必须与文件名一致,包括大小写
# model/Model.py 的gets getOneByWhere all函数会调用子类的get以继承子类get函数的效果
# 但是不会继承装饰器get的效果，因为装饰器可能会使用以上函数，形成循环或重复调用

class Model:
    table_name = ''    # 数据表名,应该与class名称和文件名一致.为空则不自动创建表
    column_names = ()  # 需要自动insert或update的字段列表,子类不能为空
    primary_key = None # 表的主键名，不推荐修改
    decorator = []     # 此model使用的装饰器，后装饰的先运行

    def __init__(self):
        if self.primary_key == None:
            self.primary_key = self.table_name+'id'
        assert(isinstance(self.table_name, str))
        assert(len(self.table_name) > 0)
        assert(' ' not in self.table_name)
        assert(isinstance(self.primary_key, str))
        assert(len(self.primary_key) > 0)
        assert(isinstance(self.column_names, list) or isinstance(self.column_names, tuple))
        assert(len(self.column_names) > 0) # column_names不能为空
        self.db = DBHelper.DBHelper()

    def get(self, item_id):
        query  = self.replaceAttr('select * from {$table_name} where {$primary_key}=%s')
        exists = self.db.fetchOne(query, item_id)
        return ModelData(exists, self) if exists else None

    # 插入一个数据，type(data)为dict或web.Storage
    # 返回新数据的主键值(primary key)
    def insert(self, data):
        data = self._formatInsertData(data)
        data = self._removeNone(data)
        assert(data is not None)
        self._insertValidate(data)
        insert_cols =   [c       for c in self.column_names if c in data.keys()]
        insert_values = [data[c] for c in self.column_names if c in data.keys()]
        query = self.replaceAttr('insert into {$table_name} (%s) values (%s)' % (','.join(insert_cols), ','.join(len(insert_cols)*['%s'])))
        return self.db.insert(query, tuple(insert_values))

    # 替换插入，当primary key或者某个unique key冲突时，即替换原有数据
    # 注意替换后primary key会被更新, 并返回此值
    def replaceInsert(self, data):
        data = self._formatInsertData(data)
        data = self._removeNone(data)
        assert(data is not None)
        self._insertValidate(data)
        insert_cols =   [c       for c in self.column_names if c in data.keys()]
        insert_values = [data[c] for c in self.column_names if c in data.keys()]
        query = self.replaceAttr('replace into {$table_name} (%s) values (%s)' % (','.join(insert_cols), ','.join(len(insert_cols)*['%s'])))
        return self.db.insert(query, tuple(insert_values))

    # 更新数据，item_id为主键id，保存data中出现的新值
    def update(self, item_id, data):
        try:
            data = self._formatUpdateData(data)
            data = self._removeNone(data)
            assert(data is not None)
            self._updateValidate(data)
            update_cols =   [c       for c in self.column_names if c in data.keys()]
            update_values = [data[c] for c in self.column_names if c in data.keys()]
            if len(update_cols) == len(update_values) > 0:
                query = self.replaceAttr('update {$table_name} set %s where {$primary_key}=%%s'
                        % (','.join([c+'=%s' for c in update_cols])) )
                affected = self.db.update(query, update_values + [item_id])
            else:
                affected = 0
        except:
            print 'ERROR INFO:'
            print 'data is :', data
            raise
        return affected

    def delete(self, item_id):
        query = self.replaceAttr('delete from {$table_name} where {$primary_key}=%s')
        return self.db.delete(query, item_id)

    # 继承了get所做的事情. 虽会有多次查询，不要怕. 宁花机器一分，不花程序员一秒
    def gets(self, item_ids):
        assert(isinstance(item_ids, list) or isinstance(item_ids, tuple))
        return map(self.get, item_ids)

    # 根据env dict返回多个数据的list
    # env的可选参数以及样例分别有:
    # select: username, email
    # from: User
    # where: ['age>%s', (18,)]
    # orderby: 'Userid desc'
    # groupby: 'Userid'
    # limit: (0, 10)
    # distinct: True
    def all(self, env=None):
        query, argv = self._spliceQuery(env)
        query = self.replaceAttr(query)
        return [ModelData(one, self) for one in self.db.fetchSome(query, argv)]

    # 用例: user_model.getOneByWhere('sex=%s and age>%s', '男', 18)
    # getOneByWhere会调用一次self.get, 以继承get函数, 但是仅调用model的get，而不是装饰器的get
    def getOneByWhere(self, where, *argv):
        assert not any(map(lambda x:isinstance(x, (tuple, list, dict, sh.storage_class)), argv))
        query  = self.replaceAttr('select * from {$table_name} where %s' % where)
        exists = self.db.fetchOne(query, argv)
        return ModelData(self.get(exists.get(self.primary_key)), self) if exists else None

    # 根据env获得count(*)值
    def getCount(self, env={}):
        env = sh.copy(env)
        env['select'] = 'count(*)' 
        if env.has_key('limit'):
            del env['limit'] # mysql语法中count(*)和limit不能一起用
        query, argv = self._spliceQuery(env)
        query = self.replaceAttr(query)
        return self.db.fetchFirst(query, argv)

    # 用model的属性值替换query中的{$xxx}
    def replaceAttr(self, query):
        ret_query = query
        for variable in re.compile('{\$\w+}').findall(query):
            ret_query = ret_query.replace(variable, getattr(self, variable[2:-1]))
        return ret_query

    # 根据表定义，获得字段类型,及其相关属性
    def getColumnTypes(self, column_names=None):
        text_min_length = 500 # 字符串长度大于多少就识别为text
        if column_names is None: column_names = self.column_names

        table_template = self.replaceAttr(self.table_template)
        columns = [sh.splitAndStrip(c) for c in self._splitTableTemplate(table_template) \
                if not any(map(lambda x: c.lower().startswith(x), ['key ','key(','primary ','unique ']))]
        columns = [c for c in columns if c[0] in column_names]
        type_keys = {
            'int': ['int', 'tinyint', 'smallint', 'mediumint', 'integer', 'bigint', 'year'], 
            'str': ['char', 'varchar', 'set', ],
            'text': ['text', 'blob', 'tinytext', 'tinyblob', 'mediumblob', 'mediumtext', 'longblob', 'longtext', ],
            'enum': ['enum', ],
            'time': ['date', 'datetime', 'timestamp', 'time'],
            'float': ['float', 'double', 'real', 'decimal', 'numeric'],
        }

        column_types = sh.storage()
        for column in columns:
            column_name = column[0]
            all_describle = column[1:]
            for index, describle in enumerate(all_describle):
                for key, values in type_keys.items():
                    accurate_type = describle.lower().partition('(')[0].lower()
                    if accurate_type in values:


                        ct = sh.storage({'type': key})

                        type_comment = describle.lower().partition('(')[2].rpartition(')')[0].strip()
                        if type_comment.isdigit():
                            ct.length = int(type_comment)

                        if key == 'str' and ct.get('length', 0) > text_min_length:
                            ct['type'] = 'text'

                        ct.accurate_type = accurate_type

                        ct.null = not ('null' in all_describle and 'not' in all_describle \
                            and all_describle.index('null') == all_describle.index('not')+1)

                        if 'default' in all_describle:
                            ct.default = all_describle[all_describle.index('default')+1]
                            if ct.default.isdigit():
                                ct.default = int(ct.default)
                            elif ct.default == 'current_timestamp':
                                ct.default = ''
                            else:
                                ct.default = ct.default.strip("'")

                        if key == 'int':
                            ct.unsigned = 'unsigned' in all_describle

                        if key == 'enum':
                            ct.options = []
                            i = index
                            while True:
                                ct.options.append(all_describle[i])
                                if ')' in all_describle[i]:
                                    break
                                i += 1
                            ct.options = ''.join(ct.options).partition('(')[2].partition(')')[0]
                            ct.options = [o.strip("'") for o in ct.options.split(',')]

                        column_types[column_name] = ct
                        break
                if column_types.has_key(column_name): break
            else:
                raise Exception('找不到数据类型:%s' % ' '.join(column))

        column_types['__column_names'] = [c for c in column_names if column_types.has_key(c)]

        return column_types

    # 使用table_template字段创建数据表
    def createTable(self):
        assert(len(self.table_name)>0)
        assert(len(self.table_template)>0)
        assert(not self.db.isTableExists(self.table_name))
        try:
            query = self.replaceAttr(self.table_template)
            self.db.executeQuery(query)
        except:
            print query
            raise

    # 根据table_template在原有表上添加新字段, 但不添加新的索引(为了保证线上数据稳定)
    def increaseCreateTable(self):
        assert(len(self.table_name)>0)
        assert(len(self.table_template)>0)
        assert(self.db.isTableExists(self.table_name))
        def getAlterQuerys(table_template):
            columns = self._splitTableTemplate(table_template)
            columns = [(c.split()[0], c) for c in columns if all(map(lambda x: not c.lower().startswith(x), ['key ','key(','primary ','unique ']))]
            exists_columns = map(str.lower, self.db.getTableColumns(self.table_name))
            return [c for c in columns if c[0].lower() not in exists_columns]
        try:
            query = self.replaceAttr(self.table_template)
            for column_name, alter_query in getAlterQuerys(query):
                try:
                    self.db.executeQuery(self.replaceAttr('alter table {$table_name} add %s' % alter_query))
                except:
                    print 'alter query is:'
                    print 'alter table %s add %s' % (self.table_name, alter_query)
                    raise
        except:
            print 'formated creat query is:'
            print query
            raise

    def _splitTableTemplate(self, table_template):
        table_template = re.sub(r'\s+', ' ', table_template.partition('(')[2].rpartition(')')[0])
        columns= []
        column = []
        bracket_count = 0
        for c in table_template + ',':
            if c == '(':
                bracket_count += 1
                column.append(c)
            elif c == ')':
                bracket_count -= 1
                column.append(c)
            elif bracket_count == 0 and c == ',':
                column = ''.join(column).strip()
                columns.append(column)
                column = []
            else:
                column.append(c)
            if bracket_count < 0:
                raise Exception('table template is invalid: ' + table_template)
        return columns

    # 对insert的数据进行预处理
    def _formatInsertData(self, data):
        return data

    # 对update的数据进行预处理
    def _formatUpdateData(self, data):
        return data

    # 对insert的数据进行断言
    def _insertValidate(self, data):
        pass

    # 对update的数据进行断言
    def _updateValidate(self, data):
        pass

    def _removeNone(self, data):
        ret_data = sh.copy(data)
        for k,v in data.items():
            if v is None:
                del ret_data[k]
        return ret_data

    # 使用env生成query和argv
    # 注意，不能把env的默认值改为{}, 否则env将成为_spliceQuery函数的一个全局属性
    def _spliceQuery(self, env=None):
        if env is None:
            env = {}
        query = 'select '
        argv = []
        assert(type(env) in [dict, sh.storage_class])

        if env.get('select', None):
            query += env['select'] + ' '
        else:
            if env.get('distinct', None):
                query += 'distinct '
            query += '* '

        if env.get('from', None):
            query += 'from '+ env['from'] + ' '
        else:
            query += 'from '+ self.table_name + ' '

        if env.get('where', None) != None:
            assert isinstance(env['where'], (tuple, list)) and len(env['where']) >= 1
            assert not any(map(lambda x:isinstance(x, (tuple, list, dict, sh.storage_class)), env['where']))
            query += ' where ' + env['where'][0] + ' '
            argv.extend(env['where'][1:])

        if env.get('groupby', None):
            query += ' group by '+env.get('groupby')

        if env.get('orderby', None):
            query += ' order by '+env.get('orderby')

        if env.get('limit', None):
            assert( type(env['limit']) in (tuple, list) and  len(env['limit']) == 2 )
            query += ' limit %s, %s'
            argv.append(env['limit'][0])
            argv.append(env['limit'][1])

        return query, argv

    # table_template变量名不能以下划线"_"开头，因为_开头的“类静态”数据将不会被子类overwrite
    # 而Model要求每个子类会调用自己的table_template变量，而不使用父类的
    table_template = \
        ''' CREATE TABLE {$table_name} (
            {$table_name}id int unsigned not null auto_increment,
            primary key ({$table_name}id)
        )ENGINE=InnoDB; '''

# model返回的数据类型,在dict的基础上实现通过d.abc代替d['abc']
# 当返回值d拥有某个model的主键值时,比如Userid,则可以通过d.user.email来直接访问相关数据
# 还可以通过后缀s访问一对多的数据,比如如果Comment表有一个Bookid属性
# 那么可以通过b.comments来获得这本书的所有评论
class ModelData(web.Storage):
    model_names = {} # 在__init__文件中记录所有model的小写到大写的关系

    def __init__(self, data, model):
        assert(data is not None)
        assert(isinstance(data, dict))
        assert(model is not None)
        web.Storage.__init__(self, data)
        self._table_name   = model.table_name
        self._primary_key  = model.primary_key
        self._class_name   = model.__module__.__class__
        self._column_names = model.column_names

    def __getattr__(self, key):
        db = DBHelper.DBHelper()
        try:
            if key == 'id': key = self._primary_key
            return web.Storage.__getattr__(self, key)
        except AttributeError:
            key = key.replace('_', '') # 以方便item.abc_def替代item.abcdef
            if ModelData.model_names.has_key(key):
                model_name = ModelData.model_names[key]
                table_name = model_name.rpartition('.')[2]
                if self.has_key(table_name + 'id'):
                    try:
                        return sh.model(model_name).get(self.get(table_name + 'id'))
                    except:
                        print 'ERROR: ModelData找不到属性', key
                        raise
            if key.endswith('s') and ModelData.model_names.has_key(key[:-1]):
                model_name = ModelData.model_names[key[:-1]]
                table_name = model_name.rpartition('.')[2]
                id_key = self.get('_table_name') + 'id'
                if db.isColumnExists(table_name, id_key):
                    try:
                        return sh.model(model_name).all({'where': [id_key + '=%s', self.id]})
                    except:
                        print 'ERROR: ModelData找不到属性', key
                        raise
            raise

    def __setattr__(self, key, value):
        # 不能对id赋值,因为__getattr__会对id做特殊判断,导致赋值失效
        assert(key != 'id')
        web.Storage.__setattr__(self, key, value)
