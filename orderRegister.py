# 注册指令，每个函数上面的 @... 的第二个参数为函数功能说明
import threading
from sys import exit
from src.basic.orderAnalyser import OrderAnalyser
from src.fqBug import FQBug
from src.reader import AutoReader, htmlReader
from src.setting import Setting
from src.shelfManager import ShelfManager

# 指令解析
rootOrder = OrderAnalyser()
rootOrder.register('exit', '退出')(exit)

# 修改设置
setting = Setting()


@rootOrder.register('set', 'set [key] [value]\n'
                           ' 修改默认设置，支持以下设置项\n'
                           ' readSpeed: float 命令行阅读器阅读速度（字/秒）\n'
                           ' autoCls: 0/1 是否开启命令行自动刷新\n'
                           ' hReadTemplate: html阅读器模板，输入 ./html/ 文件夹下的文件名\n'
                           ' color: main_GUI的配色方案，可选0~3，分别对应活力橙, 暗夜黑, 经典白, 靛紫青')
def set_(key, value):
    if key in setting:
        p, n = setting.set(key, value)
        return '已将 {} 项从 {} 修改为 {}'.format(key, p, n)
    else:
        return '{} 项不存在'.format(key)


# 书架
shelfOrder = OrderAnalyser()
rootOrder.register('shelf', 'shelf ...\n 书架指令集')(shelfOrder)
shelfManager = ShelfManager()
reader = AutoReader(shelfManager.saveShelf)
threading.Thread(target=reader.run, daemon=True).start()


@shelfOrder.register('show', 'shelf show\n 显示书架所有书籍')
def shelfShow():
    # books: [book1, book2, ...]
    # book: {'bookName', 'author', 'wordNumber', 'chapterNumber', 'src', 'progress'}
    books = shelfManager.getShelf()
    result = ''
    if not books:
        return '您的书架空空如也'
    for i, book in enumerate(books):
        result += '{}. {}\n'.format(i + 1, shelfManager.formatBook(book))
    return result


@shelfOrder.register('add', 'shelf add [bookName=all] [author=匿名]\n'
                            ' 将要添加的书籍文件（bookName.txt）放入./data/import/目录下，执行命令后可添加到书架\n'
                            ' bookName=all时，将 ./data/import/ 目录下所有文件添加到书架')
def shelfAdd(bookName='all', author='匿名'):
    return shelfManager.addFromFile(bookName, author)


@shelfOrder.register('search', 'shelf search [keywords]\n 在书架内关键字搜索\n keywords支持空格')
def shelfSearch(*keywords):
    # books: [book1, book2, ...]
    # book: {'bookName', 'author', 'wordNumber', 'chapterNumber', 'src', 'progress'}
    books = shelfManager.search(' '.join(keywords))
    result = ''
    for i, book in enumerate(books):
        result += '{}. {}\n'.format(i + 1, shelfManager.formatBook(book))
    return result


@shelfOrder.register('remove', 'shelf remove [index]\n'
                               ' 使用 shelf search/show 后，在书架中删除index项\n'
                               ' 当index非数字时，使用搜索到匹配程度最高的结果作为目标')
def shelfRemove(index):
    book = shelfManager.remove(index)
    return '已删除：{}'.format(shelfManager.formatBook(book))


@shelfOrder.register('export', 'shelf export [index=None]\n'
                               ' 使用 shelf search/show 后，将index项导出到 ./data/export/ 文件夹\n'
                               ' index取默认值时导出全部书籍\n'
                               ' 当index非数字时，使用搜索到匹配程度最高的结果作为目标')
def shelfExport(index=None):
    book = shelfManager.export(index)
    if index is None:
        result = ''
        for b in book:
            result += '已导出：{}\n'.format(shelfManager.formatBook(b))
        result += '请前往 ./data/export/ 文件夹查看'
    else:
        result = '已导出：{}\n请前往 ./data/export/ 文件夹查看'.format(shelfManager.formatBook(book))
    return result


@rootOrder.register('read', 'read [index] [chapter=None]\n'
                            ' 使用shelf search/show 后，阅读index项书籍\n'
                            ' chapter取默认值时为当前阅读进度\n'
                            ' 当index非数字时，使用搜索到匹配程度最高的结果作为目标')
def read(index, chapter=None):
    book = shelfManager.getBookByIndex(index)
    novel = shelfManager.getBookChapters(book)
    progress = book['progress'] if chapter is None else [int(chapter) - 1, 0]  # 阅读进度
    reader.loadNovel(book, novel, *progress)
    reader.switch(True)
    return '已开启命令行阅读模式'


@rootOrder.register('hread', 'hread [index] [chapter=None]\n'
                             ' 使用shelf search/show 后，使用html阅读index项书籍\n'
                             ' html阅读器的阅读进度单独存储，不与novelManager的阅读进度共享\n'
                             ' 当novelManager阅读进度发生变化时，使用hread将自动同步到novelManager的进度\n'
                             ' 使用hread后将在 ./data/export/ 中产生html文件，下次阅读时可直接打开该文件\n'
                             ' 当index非数字时，使用搜索到匹配程度最高的结果作为目标')
def hRead(index, chapter=None):
    # 获取index对应的书籍
    book = shelfManager.getBookByIndex(index)
    # 获取书名及内容
    bookName = book['bookName']
    bookContent = [chap.split('\n') for chap in shelfManager.getBookChapters(book)]  # [[para1, para2, ...] #chap1, ...]
    # 获取阅读进度
    if chapter is None:
        chapter = book['progress'][0]
    else:  # 限制章节范围
        chapter = int(chapter) - 1
        chapter = min(len(bookContent) - 1, chapter)
        chapter = max(chapter, 0)
    path = shelfManager.exportPath / (bookName + '.html')
    result = htmlReader(bookName, bookContent, chapter, path, setting['hReadTemplate'])
    return result


# 书城
cityOrder = OrderAnalyser()
rootOrder.register('city', 'city ...\n 书城指令集')(cityOrder)
fq = FQBug()


@cityOrder.register('search', 'city search [keywords]\n 在书城中关键字搜索')
def citySearch(*keywords):
    keywords = ' '.join(keywords)
    # books: [book1, book2, ...]
    # book: {'bookName', 'author', 'wordNumber', 'chapterNumber'}
    books = fq.search(keywords)
    result = ''
    for i, book in enumerate(books):
        result += '{}. {}\n'.format(i + 1, shelfManager.formatBook(book))
    return result


@cityOrder.register('add', 'city add [index]\n 将书城搜索的结果序号对应的书籍添加到书城\n keywords支持空格')
def cityAdd(index):
    if type(index) == str:
        index = int(index) - 1
    if not 0 <= index < len(fq.books):
        return '序号错误，请先使用city search搜索后，再添加相应书籍'
    book = fq.books[index]
    return shelfManager.addFromCity(book)


@cityOrder.register('update', 'city update\n'
                              ' 更新书架上所有从书城中添加的书籍\n'
                              ' 每更新5章会自动保存，可以随时中断程序')
def cityUpdate():
    for book in shelfManager.getShelf():
        if book['src'].isdigit():  # 书籍来源为city，可更新
            chapters = fq.getChapters(book['src'])  # 章节id + 章节标题 的列表
            cc = shelfManager.getBookChapters(book)  # 本地的章节列表
            for i, chapter in enumerate(chapters[len(cc):]):  # 从最新章节开始更新
                text = chapter[1] + fq.getText(chapter[0])
                cc.append(text)
                print('已更新：《{}》 {}\t字数：{}'.format(book['bookName'], chapter[1], len(text)))
                # 保存
                if i % 5 == 0:
                    shelfManager.getBookPath(book).write(cc)
                    shelfManager.update()
            shelfManager.getBookPath(book).write(cc)  # 保存
            shelfManager.update()
    return '已全部更新完毕'
