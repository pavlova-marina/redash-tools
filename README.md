# redash_tools

Пакет содержит функции для работы с Redash через API, а также классы `RedashSession`, `Query`, `Dashboard`, `QueryTemplate`, `DashboardTemplate`, которые можно использовать для создания новых функций / инструментов.

Основные возможности `redash_tools`:
* считывание запросов / дашбордов из заданного инстанса Redash
* загрузка запросов / дашбордов в заданный инстанс Redash
* считывание запросов / дашбордов из файловой системы и сохранение в файловую систему
* перенос запросов / дашбордов с одного инстанса на другой
* преобразование запроса / дашборда в шаблон с указанием параметров, по которым будет произведена шаблонизация
* рендер запроса / дашборда из шаблона, используя заданные значения параметров
* батч-редактирование на уровне запросов / дашбордов:
	* простановка тегов по списку `id`
	* установка расписания по списку `id`
	* архивирование/восстановление запросов по списку `id`
	* автозамена в теле запроса по точному соответствию/регулярному выражению
	* изменение типа параметров дашборда с widget-level на dashboard-level
	
	
## Установка пакета на локальный компьютер

Установить пакет можно с помощью pip install

```
pip install redash-tools
```

После установки все имеющиеся функции и классы можно использовать в консоли Python и при создании новых скриптов.
В будущем планируется создание CLI для данного пакета.

## Начало работы

Для использования инструментов `redash_tools` нужно импортировать соответствующий пакет.

```python
import redash_tools as rt
```

Затем нужно инициализировать сессию подключения к Redash. Для этого надо в качестве аргументов указать URL инстанса Redash (включая http:// или https://) и API-ключ пользователя. Либо можно оставить скобки пустыми, для интерактивного ввода

```python
redash = rt.RedashSession()
```

Если url и API-ключ не указаны, будет запрошено ввести url и API-ключ пользователя. API-ключ можно найти в профиле зарегистрированного пользователя Redash, он обладает теми же правами, что и данный пользователь.

Используя объект RedashSession, можно отправлять в данную сессию GET, POST, DELETE запросы, а также выполнять более специализированные методы:

Метод RedashSession().get_query() возвращает объект класса Query.
```python
query = rt.RedashSession().get_query(1)
```

Метод RedashSession().get_dashboard() возвращает объект класса Dashboard.
```python
dashboard = rt.RedashSession().get_dashboard('test')
```

Объекты классов Query, Dashboard имеют методы to_file(path), to_redash(redash_session) для отправки содержимого, соответственно, в файловую систему либо для загрузки в нужный инстанс Redash.

Объект класса Query или Dashboard можно превратить в шаблон с помощью метода to_template(param_names). Метод возвращает объект класса QueryTemplate или DashboardTemplate соответственно.

Объект класса QueryTemplate / DashboardTemplate можно отрендерить в Query / Dashboard указав конкретные значения параметров в виде словаря:

```python
template = rt.RedashSession().get_query(1).to_template(['param_name'])
query = template.render({'param_name': param_value})
```

Шаблоны также можно сохранять в файловой системе с помощью метода to_file, но нельзя непосредственно заливать в Redash (сначала их нужно отрендерить).
Данные сущности можно импортировать из пакета и использовать в интерактивном режиме или для создания своих скриптов.

Пример кода для создания в редаше нового запроса/нового дашборда:

```python
...
```

Пример кода для создания серии шаблонизированных дашбордов:

```python
import redash_tools as rt
rs = rt.RedashSession('<url>', '<API_KEY>')
db = rs.get_dashboard('test')
t = db.to_template(['country'])
for c in ['Russia', 'France', 'Italy']:
    d = t.render({'country': c}, slug = f'dashboard_{c}', name = f'{c}: Dashboard')  # example of custom naming
    d.to_redash(rs)
```    


## tools 





