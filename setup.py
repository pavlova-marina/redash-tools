from setuptools import setup, find_packages


setup(name='redash_tools',
      version='1.0.1',
      description='Tools to backup, batch update, template redash queries and dashboards',
      url='http://github.com/pavlova-marina/redash_tools',
      author='Marina Pavlova',
      author_email='pavlova.marina.v@gmail.com',
      packages=find_packages(),
      classifiers=["Programming Language :: Python :: 3",
                   "Operating System :: OS Independent",
                   ],
      install_requires=['requests',
                        ],
      python_requires='>=3.6'
      )