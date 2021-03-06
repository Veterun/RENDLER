#!/usr/bin/env python

from collections import deque
import json
import os
import signal
import sys
import time
import datetime
from threading import Thread

try:
    from mesos.native import MesosExecutorDriver, MesosSchedulerDriver
    from mesos.interface import Executor, Scheduler
    from mesos.interface import mesos_pb2
except ImportError:
    from mesos import Executor, MesosExecutorDriver, MesosSchedulerDriver, Scheduler
    import mesos_pb2

import results
import task_state
import export_dot

TASK_CPUS = 0.1
TASK_MEM = 32
SHUTDOWN_TIMEOUT = 30  # in seconds
LEADING_ZEROS_COUNT = 5  # appended to task ID to facilitate lexicographical order
TASK_ATTEMPTS = 5  # how many times a task is attempted

# See the Mesos Framework Development Guide:
# http://mesos.apache.org/documentation/latest/app-framework-development-guide
#
# Scheduler, scheduler driver, executor, and executor driver definitions:
# https://github.com/apache/mesos/blob/master/src/python/src/mesos.py
# https://github.com/apache/mesos/blob/master/include/mesos/scheduler.hpp
#
# Mesos protocol buffer definitions for Python:
# https://github.com/mesosphere/deimos/blob/master/deimos/mesos_pb2.py
# https://github.com/apache/mesos/blob/master/include/mesos/mesos.proto
#
class RenderingCrawler(Scheduler):
    def __init__(self, seedUrl, maxRenderTasks, crawlExecutor, renderExecutor):
        print "RENDLER"
        print "======="
        print "seedUrl: [%s]\n" % seedUrl
        self.seedUrl = seedUrl
        self.crawlExecutor  = crawlExecutor
        self.renderExecutor = renderExecutor
        self.crawlQueue = deque([seedUrl])
        self.renderQueue = deque([seedUrl])
        self.processedURLs = set([seedUrl])
        self.crawlResults = set([])
        self.renderResults = {}
        self.tasksCreated  = 0
        self.tasksRunning = 0
        self.tasksFailed = 0
        self.tasksRetrying = {}
        self.renderLimitReached = False
        self.maxRenderTasks = maxRenderTasks
        self.shuttingDown = False

    def registered(self, driver, frameworkId, masterInfo):
        """
          Invoked when the scheduler successfully registers with a Mesos master.
          It is called with the frameworkId, a unique ID generated by the
          master, and the masterInfo which is information about the master
          itself.
        """
        print "Registered with framework ID [%s]" % frameworkId.value

    def reregistered(self, driver, masterInfo):
        """
          Invoked when the scheduler re-registers with a newly elected Mesos
          master.  This is only called when the scheduler has previously been
          registered.  masterInfo contains information about the newly elected
          master.
        """
        print "Re-registered with Mesos master"

    def disconnected(self, driver):
        """
          Invoked when the scheduler becomes disconnected from the master, e.g.
          the master fails and another is taking over.
        """
        pass

def makeTaskPrototype(self, offer):
    task = mesos_pb2.TaskInfo()
    tid = self.tasksCreated
    self.tasksCreated += 1
    task.task_id.value = str(tid).zfill(LEADING_ZEROS_COUNT)
    task.slave_id.value = offer.slave_id.value
    cpus = task.resources.add()
    cpus.name = "cpus"
    cpus.type = mesos_pb2.Value.SCALAR
    cpus.scalar.value = TASK_CPUS
    mem = task.resources.add()
    mem.name = "mem"
    mem.type = mesos_pb2.Value.SCALAR
    mem.scalar.value = TASK_MEM
    return task

    def makeCrawlTask(self, url, offer):
        task = self.makeTaskPrototype(offer)
        task.name = "crawl task %s" % task.task_id.value
        #
        # TODO
        #
        # 
        pass

    def makeRenderTask(self, url, offer):
        task = self.makeTaskPrototype(offer)
        task.name = "render task %s" % task.task_id.value
        #
        # TODO
        #
        pass
    
    def retryTask(self, task_id, url):
        if not url in self.tasksRetrying:
            self.tasksRetrying[url] = 1
            
        if self.tasksRetrying[url] < TASK_ATTEMPTS:
            self.tasksRetrying[url] += 1
            ordinal = lambda n: "%d%s" % (n, \
              "tsnrhtdd"[(n / 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])
            print "%s try for \"%s\"" % \
              (ordinal(self.tasksRetrying[url]), url)

            if task_id.endswith(CRAWLER_TASK_SUFFIX):
              self.crawlQueue.append(url)
            elif task_id.endswith(RENDER_TASK_SUFFIX):
              self.renderQueue.append(url)
        else:
            self.tasksFailed += 1
            print "Task for \"%s\" cannot be completed, attempt limit reached" % url

    def printStatistics(self):
        print "Queue length: %d crawl, %d render; Tasks: %d running, %d failed" % (
          len(self.crawlQueue), len(self.renderQueue), self.tasksRunning, self.tasksFailed
        )

    def maxTasksForOffer(self, offer):
        count = 0
        cpus = next(rsc.scalar.value for rsc in offer.resources if rsc.name == "cpus")
        mem = next(rsc.scalar.value for rsc in offer.resources if rsc.name == "mem")
        #
        # TODO
        #
        pass

    def resourceOffers(self, driver, offers):
        """
          Invoked when resources have been offered to this framework. A single
          offer will only contain resources from a single slave.  Resources
          associated with an offer will not be re-offered to _this_ framework
          until either (a) this framework has rejected those resources (see
          SchedulerDriver.launchTasks) or (b) those resources have been
          rescinded (see Scheduler.offerRescinded).  Note that resources may be
          concurrently offered to more than one framework at a time (depending
          on the allocator being used).  In that case, the first framework to
          launch tasks using those resources will be able to use them while the
          other frameworks will have those resources rescinded (or if a
          framework has already launched tasks with those resources then those
          tasks will fail with a TASK_LOST status and a message saying as much).
        """
        self.printStatistics()
        print "Received resource offer(s)"
        #
        # TODO
        #
        pass

    def offerRescinded(self, driver, offerId):
        """
          Invoked when an offer is no longer valid (e.g., the slave was lost or
          another framework used resources in the offer.) If for whatever reason
          an offer is never rescinded (e.g., dropped message, failing over
          framework, etc.), a framwork that attempts to launch tasks using an
          invalid offer will receive TASK_LOST status updats for those tasks
          (see Scheduler.resourceOffers).
        """
        pass

    def statusUpdate(self, driver, update):
        """
          Invoked when the status of a task has changed (e.g., a slave is lost
          and so the task is lost, a task finishes and an executor sends a
          status update saying so, etc.) Note that returning from this callback
          acknowledges receipt of this status update.  If for whatever reason
          the scheduler aborts during this callback (or the process exits)
          another status update will be delivered.  Note, however, that this is
          currently not true if the slave sending the status update is lost or
          fails during that time.
        """
        stateName = task_state.nameFor[update.state]
        print "Task [%s] is in state [%s]" % (update.task_id.value, stateName)

    def frameworkMessage(self, driver, executorId, slaveId, message):
        """
          Invoked when an executor sends a message. These messages are best
          effort; do not expect a framework message to be retransmitted in any
          reliable fashion.
        """
        o = json.loads(message)

        if executorId.value == crawlExecutor.executor_id.value:
            result = results.CrawlResult(o['taskId'], o['url'], o['links'])
            #
            # TODO
            #

        elif executorId.value == renderExecutor.executor_id.value:
            result = results.RenderResult(o['taskId'], o['url'], o['imageUrl'])
            #
            # TODO
            #

    def slaveLost(self, driver, slaveId):
        """
          Invoked when a slave has been determined unreachable (e.g., machine
          failure, network partition.) Most frameworks will need to reschedule
          any tasks launched on this slave on a new slave.
        """
        pass

    def executorLost(self, driver, executorId, slaveId, status):
        """
          Invoked when an executor has exited/terminated. Note that any tasks
          running will have TASK_LOST status updates automatically generated.
        """
        pass

    def error(self, driver, message):
        """
          Invoked when there is an unrecoverable error in the scheduler or
          scheduler driver.  The driver will be aborted BEFORE invoking this
          callback.
        """
        print "Error from Mesos: %s " % message

def hard_shutdown():  
    driver.stop()

def graceful_shutdown(signal, frame):
    print "RENDLER is shutting down"
    rendler.shuttingDown = True
    
    wait_started = datetime.datetime.now()
    while (rendler.tasksRunning > 0) and \
      (SHUTDOWN_TIMEOUT > (datetime.datetime.now() - wait_started).total_seconds()):
        time.sleep(1)
    
    if (rendler.tasksRunning > 0):
        print "Shutdown by timeout, %d task(s) have not completed" % rendler.tasksRunning

    hard_shutdown()

#
# Execution entry point:
#
if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print "Usage: %s seedUrl mesosMasterUrl [maxRenderTasks]" % sys.argv[0]
        sys.exit(1)

    baseURI = "/home/vagrant/hostfiles"
    suffixURI = "python"
    uris = [ "crawl_executor.py",
             "export_dot.py",
             "render_executor.py",
             "results.py",
             "task_state.py" ]
    uris = [os.path.join(baseURI, suffixURI, uri) for uri in uris]
    uris.append(os.path.join(baseURI, "render.js"))

    crawlExecutor = mesos_pb2.ExecutorInfo()
    crawlExecutor.executor_id.value = "crawl-executor"
    crawlExecutor.command.value = "python crawl_executor.py"

    for uri in uris:
        uri_proto = crawlExecutor.command.uris.add()
        uri_proto.value = uri
        uri_proto.extract = False

    crawlExecutor.name = "Crawler"

    renderExecutor = mesos_pb2.ExecutorInfo()
    renderExecutor.executor_id.value = "render-executor"
    renderExecutor.command.value = "python render_executor.py --local"

    for uri in uris:
        uri_proto = renderExecutor.command.uris.add()
        uri_proto.value = uri
        uri_proto.extract = False

    renderExecutor.name = "Renderer"

    framework = mesos_pb2.FrameworkInfo()
    framework.user = "" # Have Mesos fill in the current user.
    framework.name = "RENDLER"

    try: maxRenderTasks = int(sys.argv[3])
    except: maxRenderTasks = 0
    rendler = RenderingCrawler(sys.argv[1], maxRenderTasks, crawlExecutor, renderExecutor)

    driver = MesosSchedulerDriver(rendler, framework, sys.argv[2])

    # driver.run() blocks; we run it in a separate thread
    def run_driver_async():
        status = 0 if driver.run() == mesos_pb2.DRIVER_STOPPED else 1
        driver.stop()
        sys.exit(status)
    framework_thread = Thread(target = run_driver_async, args = ())
    framework_thread.start()

    print "(Listening for Ctrl-C)"
    signal.signal(signal.SIGINT, graceful_shutdown)
    while framework_thread.is_alive():
        time.sleep(1)

    export_dot.dot(rendler.crawlResults, rendler.renderResults, "result.dot")
    print "Goodbye!"
    sys.exit(0)
