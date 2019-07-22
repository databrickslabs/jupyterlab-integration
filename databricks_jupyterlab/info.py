#   Copyright 2019 Bernhard Walter
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
   
from sidecar import Sidecar
from ipywidgets import Output
from IPython.display import display


class Info(object):
    
    instance = None
    
    class __Info(object):
        def __init__(self, spark):
            self.spark = spark

        def create(self):
            self.sc = Sidecar(title="Info")
            self.output = Output()

            with self.sc:
                display(self.output)

        def info(self, *msg):
            with self.output:
                print(*msg)

        def close(self):
            self.selects = []
            self.sc.close()
        
    def __init__(self, spark=None):
        if not Info.instance:
            Info.instance = Info.__Info(spark)
            
    def __getattr__(self, name):
        return getattr(self.instance, name)
