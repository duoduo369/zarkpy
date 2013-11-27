#coding=utf-8
import sys, os
''' 网站的配置信息 '''
# 导入cgi目录
if __name__=='__main__':
    father_dir = os.path.split(os.path.realpath(__file__))[0].rpartition('/')[0]
    if father_dir not in sys.path:
        sys.path.insert(0, father_dir)

from Model import Model
import site_helper as sh

class SiteConfig(Model):
    table_name = 'SiteConfig'
    column_names = ['name', 'value', 'title', ]
    decorator = [
        ('Pagination', dict(paging_key='page_num', paging_volume=1000, paging=False) ),
        ('StringProcess', dict(strip=['name']) ),
    ]

    table_template = \
        ''' CREATE TABLE {$table_name} (
            {$table_name}id  int unsigned not null auto_increment,
            name             varchar(100) not null default '',
            value            text charset utf8,
            title            varchar(300) charset utf8 not null default '',
            primary key      ({$table_name}id),
            unique key       (name)
        )ENGINE=InnoDB; '''

def _operateSetting(argv, usage, actions):
    try:
        assert len(argv) == 3 or len(argv) == 4
        assert argv[1] in actions
        if len(argv) == 3:
            argv.append('')
        action, name, value = argv[1:]
        model = sh.model('SiteConfig')

        exists = model.getOneByWhere('name=%s', name)

        if action == 'get':
            if exists:
                print exists.value

        elif action == 'set':
            if exists:
                model.update(exists.id, {'value': value})
            else:
                model.insert({'name': name, 'value': value})
        
        elif action == 'delete':
            if exists:
                model.delete(exists.id)

    except Exception:
        print usage

if __name__=='__main__':
    usage = 'Usage: python model/SiteConfig.py {set|get|delete}'
    usage += '\n   set key value'
    usage += '\n   get key'
    usage += '\n   delete key'
    _operateSetting(sys.argv, usage, ['set', 'get', 'delete'])
