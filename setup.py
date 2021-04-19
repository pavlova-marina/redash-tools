from setuptools import setup, find_packages

setup(name='redash_tools',
      packages=find_packages(),
      version='1.0.3',
      license='MIT',
      description='Tools to backup, batch update, template redash queries and dashboards',
      author='Marina Pavlova',
      author_email='pavlova.marina.v@gmail.com',
      url='http://github.com/pavlova-marina/redash-tools',
      download_url='https://github.com/pavlova-marina/redash-tools/archive/refs/tags/v1.0.3.tar.gz',
      keywords=['redash'],
      install_requires=['requests'],
      python_requires='>=3.6',
      classifiers=[
                  'License :: OSI Approved :: MIT License',
                  'Operating System :: OS Independent',
                  'Programming Language :: Python :: 3.6',
              ]
      )
