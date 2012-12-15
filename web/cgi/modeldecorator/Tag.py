#coding=utf-8
from Decorator import Decorator
import site_helper as sh

# 标签装饰, 如果相对你的数据打标签，可以用此装饰
# 与Category装饰器一样，标签基于名称而忽略id
# 使用此装饰不需要为model添加字段，所有model的tag数据存在Tag表中
# 你可以在data中添加data_key指定的标签值来在insert和update时自动维护tag数据
# split_char是标签数据的分割符， auto_operate可以为append或reset
# append表示自动维护时添加新的标签但是不删除原有标签，而reset会删除
# 也可以通过get(i).tags来获得某个数据的标签

class Tag(Decorator):
    ''' decorator = [
        ('Tag', dict(tag_id_key='Tagid', tag_model_name='Tag'
                data_key='tags', split_char=' ', auto_operate='append') ),
    ] '''

    # 插入数据并自动插入tag
    def insert(self, data):
        new_id = self.model.insert(data)
        self.__autoOperateTags(new_id, data.get(self.arguments.data_key, ''))
        return new_id

    # 更新数据并自动插入tag
    def update(self, item_id, data):
        self.__autoOperateTags(item_id, data.get(self.arguments.data_key, ''))
        return self.model.update(item_id, data)

    # 为某个数据添加tag
    def addTag(self, item_id, tag):
        exists = self.__getExistsTag(item_id, tag)
        return self.__insertTag(item_id, tag) if not exists else exists.id

    # 为某个数据添加多个tag
    def addTags(self, item_id, tags):
        assert(isinstance(tags, list) or isinstance(tags, tuple))
        return [self.addTag(item_id, tag) for tag in tags if self.__getExistsTag(item_id, tag) is None]

    # 重置某个数据的tag
    def resetTags(self, item_id, tags):
        assert(isinstance(tags, list) or isinstance(tags, tuple))
        self.__clearTags(item_id)
        for tag in tags:
            self.addTag(item_id, tag)

    # 获得某个数据的tag
    def getTags(self, item_id):
        return [t.name for t in self.__getTagModel().all({'where': ('data_name=%s and data_id=%s', [self.getModelTableName(), item_id])})]

    # 判断某个数据是否有某个tag
    def hasTag(self, item_id, tag):
        return self.__getExistsTag(item_id, tag) is not None

    # 删除某个数据的某个tag
    def removeTag(self, item_id, tag):
        exists = self.__getExistsTag(item_id, tag)
        return self.__deleteTag(self, exists.id) if exists else 0

    # 根据tag名称获得所有打了此tag的数据
    def getsByTag(self, tag):
        assert(isinstance(tag, str) and len(tag.strip()) > 0)
        tag_model = self.__getTagModel()
        query = tag_model.replaceAttr('select data_id from {$table_name} where data_model=%s and name=%s')
        item_ids = tag_model.db.fetchSomeFirst(query, [self.getModelTableName(), tag])
        return self.model.gets(item_ids)

    def __autoOperateTags(self, item_id, tags):
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(self.arguments.split_char) if t.strip()]
        if self.arguments.auto_operate == 'reset':
            self.__clearTags(item_id)
            return self.addTags(item_id, tags)
        elif self.arguments.auto_operate == 'append':
            return self.addTags(item_id, tags)

    # 请使用resetTags(item_id, [])来清除tags
    def __clearTags(self, item_id):
        tag_model = self.__getTagModel()
        query = tag_model.replaceAttr('delete from {$table_name} where data_model=%s and data_id=%s')
        return tag_model.db.delete(query, [self.getModelTableName(), item_id])

    def __deleteTag(self, tag_id):
        return self.__getTagModel().delete(tag_id)

    def __getExistsTag(self, item_id, tag):
        assert(isinstance(tag, str) and len(tag.strip()) > 0)
        return self.__getTagModel().getOneByWhere('data_name=%s and name=%s', [self.getModelTableName(), tag.strip()])

    def __insertTag(self, item_id, tag):
        return self.__getTagModel().insert(dict( data_name = self.getModelTableName()
            data_id = item_id, name = tag ))

    def __getTagModel(self):
        return sh.model(self.arguments.tag_model_name)