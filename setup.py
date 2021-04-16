from setuptools import setup

setup(name='redash_tools',
      packages=['redash_tools'],
      version='1.0.2',
      license='MIT',
      description='Tools to backup, batch update, template redash queries and dashboards',
      author='Marina Pavlova',
      author_email='pavlova.marina.v@gmail.com',
      url='http://github.com/pavlova-marina/redash-tools',
      download_url='https://github.com/pavlova-marina/redash-tools/archive/v1.0.2.tar.gz',
      keywords=['redash'],
      install_requires=['requests'],
      python_requires='>=3.6',
      classifiers = [
                  'Development Status :: 3 - Alpha',
                  'Intended Audience :: Developers',
                  'Topic :: Software Development :: Build Tools',
                  'License :: OSI Approved :: MIT License',
                  'Operating System :: OS Independent',
                  'Programming Language :: Python :: 3',
                  'Programming Language :: Python :: 3.4',
                  'Programming Language :: Python :: 3.5',
                  'Programming Language :: Python :: 3.6',
              ]
      )