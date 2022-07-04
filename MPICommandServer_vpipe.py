#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import print_function
import time # To handle sleep times
import traceback # To pretty-print tracebacks
import subprocess # To deploy virtual frame buffer
import tempfile
import uuid
import os
import sys
    
# Import CASA environment: Service thread stack ends at the level where it is launched,
# so we need to import the CASA tasks and various functions and  definitions here.

# Import casalog and casa dictionary
# confusingly, much of taskinit is actually about initing the casa tools
try:
    # CASA6
    import _thread # To handle service threads like monitoring
    from casatools import logsink
    casalog = logsink()

    # analog to the old importing of all tasks from taskinit in CASA 5
    # But: this has a high risk of producing circular imports.
    sys.path.append('/Users/jackradcliffe/Documents/BD228L/VLBI_pipeline')
    from VLBI_pipe_functions_MPI import *
    from casatasks import *

    # Import MPIEnvironment static class
    from casampi.MPIEnvironment import MPIEnvironment

except ImportError:
    # CASA5
    import thread as _thread
    
    from taskinit import *    
    # Import all tasks from the auto-generated tasks.py
    from tasks import *
    sys.path.append('/Users/jackradcliffe/Documents/BD228L/VLBI_pipeline')
    from VLBI_pipe_functions_MPI import *    
    # stuff needed in the task code generated from the casa2pycli xslt template
    from init_tasks import update_params, saveinputs

    # Import MPIEnvironment static class
    from .MPIEnvironment import MPIEnvironment

# Import MPICommunicator singleton
from .MPICommunicator import MPICommunicator

# Import MPIMonitorServer singleton
from .MPIMonitorServer import MPIMonitorServer

##
## toplevel frame marker
##
_casa_top_frame_ = True
__last_taskname = None


class MPICommandServer: 
    
    # Storage for the MPICommandServer singleton instance reference
    __instance = None
    
    def __init__(self,start_services=False):
        """ Create MPICommandServer singleton instance """
        
        casalog_call_origin = "MPICommandServer::__init__"
        
        # Check if MPI is effectively enabled
        if not MPIEnvironment.is_mpi_enabled:
            msg = "MPI is not enabled"
            casalog.post(msg,"SEVERE",casalog_call_origin)
            raise Exception(msg)
        
        # Check if MPIMonitorServer can be instantiated
        if MPIEnvironment.is_mpi_client:
            msg = "MPICommandServer cannot be instantiated at master MPI process"
            casalog.post(msg,"SEVERE",casalog_call_origin)
            raise Exception(msg)
        
        # Check whether we already have a MPICommandServer singleton instance
        if MPICommandServer.__instance is None:
            # Create MPICommandServer singleton instance
            MPICommandServer.__instance = MPICommandServer.__MPICommandServerImpl(start_services=start_services)

        # Store MPICommandServer singleton instance reference as the only member in the handle
        self.__dict__['_MPICommandServer__instance'] = MPICommandServer.__instance


    def __getattr__(self, attr):
        """ Delegate access to MPICommandServer implementation """
        return getattr(self.__instance, attr)


    def __setattr__(self, attr, value):
        """ Delegate access to MPICommandServer implementation """
        return setattr(self.__instance, attr, value)        
    
    
    class __MPICommandServerImpl:
        """ Implementation of the MPICommandServer singleton interface """    
    
        def __init__(self,start_services=False):

            # Initialize command request handler service state
            self.__command_request_handler_service_on = False
            self.__command_request_handler_service_running = False
            self.__command_request_handler_service_thread = None   
            
            # Request to stop serve(), sent from the client on exit/shutdown
            self.__stop_service_requested = False

            # Instantiate MPICommunicator reference
            self.__communicator = MPICommunicator()
            
            # Instantiate MPIMonitorClient reference
            self.__monitor_server = MPIMonitorServer(False)
            
            # Initialize logfile descriptor
            self.__logfile_descriptor = open(casalog.logfile(), 'a')
            
            # Initialize virtual frame buffer state
            self.__virtual_frame_buffer_port = None
            self.__virtual_frame_buffer_process = None
            
            # Automatically start services
            if start_services:
                self.start_services()
                

        ################################################################################################################            
        # Private methods ##############################################################################################
        ################################################################################################################   
        
        
        def __command_request_handler_service(self):
            
            casalog_call_origin = "MPICommandServer::command_request_handler_service"

            # Mark service as running
            self.__command_request_handler_service_running = True                        
                          
            while (self.__command_request_handler_service_on):
                
                # First check if there is a command request msg available
                msg_available = False
                try:
                    msg_available = self.__communicator.command_request_probe()
                except Exception as instance:
                    casalog.post("Exception checking if command request msg is available: %s" 
                                 % str(instance),"SEVERE",casalog_call_origin)
                    msg_available = False
                    
                # Then receive command request msg
                msg_received = False
                if (msg_available):
                    try:
                        command_request = self.__communicator.command_request_recv()
                        casalog.post("Received command request msg: %s" 
                                     % command_request['command'],MPIEnvironment.command_handling_log_level,casalog_call_origin)
                        msg_received = True
                    except:
                        formatted_traceback = traceback.format_exc()
                        casalog.post("Exception receiving command request msg: %s" 
                                     % str(formatted_traceback),"SEVERE",casalog_call_origin)
                        msg_received = False
                        
                # Finally process command request and send back response
                if (msg_received):
                    
                    # Start timer
                    command_start_time = time.time()
                                     
                    # Update server state
                    self.__monitor_server.set_status('busy',True)
                    self.__monitor_server.set_status('command',command_request['command'])
                    self.__monitor_server.set_status('command_start_time',command_start_time)            
                    # Get command request id 
                    command_request_id = command_request['id']
                    # Prepare command response
                    command_response = dict(command_request)  
                    
                    # Set command start time
                    command_response['command_start_time'] = command_start_time
                    
                    # Execute/Evaluate command request
                    try:
                        # Add dict-defined parameters to globals
                        if isinstance(command_request['parameters'], dict):
                            globals().update(command_request['parameters'])

                        # Execute command
                        if command_request['mode']=='eval':
                            casalog.post("Going to evaluate command request with id# %s as an expression via eval: %s" 
                                         % (str(command_request_id),str(command_request['command'])),
                                         MPIEnvironment.command_handling_log_level,casalog_call_origin)
                            if isinstance(command_request['parameters'], dict):
                                if command_request['command'].endswith('()'):
                                    cmd = command_request['command'][:-2]
                                    eval_str = '{0}(**{1})'.format(
                                    cmd, command_request['parameters'])
                                else:
                                    eval_str = command_request['command']

                            elif callable(command_request['command']):
                                eval_str = '{}()'.format(command_request['command'])

                            else:

                                eval_str = str(command_request['command'])

                            command_response['ret'] = eval(eval_str)
                        elif command_request['mode']=='exec':
                            casalog.post("Going to execute command request with id# %s as a statement via exec: %s" 
                                         % (str(command_request_id),command_request['command']),
                                         MPIEnvironment.command_handling_log_level,casalog_call_origin)      
                            code = compile(command_request['command'], casalog_call_origin, 'exec')                                                   
                            exec(code)
                            command_response['ret'] = None
                        elif command_request['mode']=='push':
                            casalog.post("Command request with id# %s is a push operation" 
                                         % str(command_request_id),
                                         MPIEnvironment.command_handling_log_level,casalog_call_origin)  
                            command_response['ret'] = None
                                    
                        # Set command response parameters
                        command_response['successful'] = True
                        command_response['traceback'] = None
                        
                    except Exception:
                        formatted_traceback = traceback.format_exc()
                        casalog.post("Exception executing command request via %s: %s" 
                                     % (command_request['mode'],str(formatted_traceback)),"SEVERE",casalog_call_origin)
                        # Set command response parameters
                        command_response['successful'] = False
                        command_response['traceback']=formatted_traceback
                        command_response['ret']=None
                    # Variables are cleaned from the environment regardless of the result
                    finally:
                        # Clear parameter variables
                        if isinstance(command_request['parameters'],dict) and command_request['mode']!='push':
                            for parameter in command_request['parameters']:
                                try:
                                    del globals()[parameter]
                                except:
                                    formatted_traceback = traceback.format_exc()
                                    casalog.post("Exception deleting parameter variable '%s' from global environment: %s" 
                                                 % (str(parameter),str(formatted_traceback)),"WARN",casalog_call_origin)
                                    
                    # Set command stop time
                    command_stop_time = time.time()
                    command_response['command_stop_time'] = command_stop_time
                        
                    # Update server state 
                    self.__monitor_server.set_status('busy',False)
                    self.__monitor_server.set_status('command',None)
                    self.__monitor_server.set_status('command_start_time',None)                      
                    # Send response back (successful or not)
                    try:
                        casalog.post("Command request with id %s successfully processed in %s mode, sending back response ..." 
                                     % (str(command_response['id']),str(command_response['mode'])),
                                     MPIEnvironment.command_handling_log_level,casalog_call_origin)                           
                        self.__communicator.command_response_send(response=command_response)
                    except:
                        formatted_traceback = traceback.format_exc()
                        casalog.post("Exception sending back command response: %s" 
                                     % str(formatted_traceback),"SEVERE",casalog_call_origin)                
                else:
                    time.sleep(MPIEnvironment.mpi_command_request_handler_service_sleep_time) 
        
            # Mark service as not running
            self.__command_request_handler_service_running = False            

            
        def __start_command_request_handler_service(self):
        
            casalog_call_origin = "MPICommandServer::start_command_request_handler_service"

            if self.__command_request_handler_service_running:
                casalog.post("MPI command request handler service is already running","WARN",casalog_call_origin)
                return True
            
            try:
                self.__command_request_handler_service_on = True
                self.__command_request_handler_service_thread = _thread.start_new_thread(self.__command_request_handler_service, ())
            except Exception as instance:
                self.__command_request_handler_service_on = False
                self.__command_request_handler_service_running = False
                casalog.post("Exception starting MPI command request handler service: %s" 
                             % str(instance),"SEVERE",casalog_call_origin)  
                return False
        
            while (not self.__command_request_handler_service_running):
                time.sleep(MPIEnvironment.mpi_check_start_service_sleep_time) 
        
            casalog.post("MPI command request handler service started","INFO",casalog_call_origin)
            
            return True
        
        
        def __stop_command_request_handler_service(self):
        
            casalog_call_origin = "MPICommandServer::stop_command_request_handler_service"
        
            if not self.__command_request_handler_service_running:
                casalog.post("MPI command request handler service is not running","WARN",casalog_call_origin)
                return             

            self.__command_request_handler_service_on = False
        
            while (self.__command_request_handler_service_running):
                time.sleep(MPIEnvironment.mpi_check_stop_service_sleep_time)

            casalog.post("MPI command request handler service stopped","INFO",casalog_call_origin)
      
            
        ################################################################################################################            
        # Public methods ###############################################################################################
        ################################################################################################################            
            
            
        def start_virtual_frame_buffer(self):
            """ Starts Xvfb and sets DISPLAY environment variable """

            def gen_displayport():
                """ produces display port in ':345' string format """
                displayport = os.getpid()
                while os.path.exists('/tmp/.X%d-lock' % displayport):
                    displayport += 1

                return ":%d" % displayport

            def gen_xauth_cookie():
                """ produces cookie ready to be used with xauth add """
                try:
                    cookie = subprocess.check_output(['mcookie'],
                                                     universal_newlines=True).strip()
                except Exception:
                    cookie = str(uuid.uuid4()).replace('-', '')

                return cookie

            def run_xauth_xvfb(xauth_dir, xauthfile, port, cookie):
                """ runs xauth + Xvfb similarly as xvfb-run """
                subprocess.call(['xauth', '-f', xauthfile.name, 'add', port, '.', cookie],
                                stdout=self.__logfile_descriptor,
                                stderr=self.__logfile_descriptor)

                self.__virtual_frame_buffer_process = subprocess.Popen(
                    ['Xvfb', port, '-auth', xauthfile.name],
                    stdout=self.__logfile_descriptor, stderr=self.__logfile_descriptor,
                    shell=False)

                try:
                    subprocess.call(['xauth', '-f', xauthfile.name, 'remove', port],
                                    stdout=self.__logfile_descriptor,
                                    stderr=self.__logfile_descriptor)
                    xauthfile.close()
                    if os.path.isdir(xauth_dir):
                        os.rmdir(xauth_dir)
                except OSError as exc:
                    casalog.post("xauth file and its subdirectory could not be removed "
                                 "cleanly: {0}, with exception: {1}".
                                 format(xauthfile.name, exc), "WARN",
                                 casalog_call_origin)

            casalog_call_origin = "MPICommandServer::start_virtual_frame_buffer"

            self.__virtual_frame_buffer_port = gen_displayport()
            xauth_dir = tempfile.mkdtemp(prefix='CASA_MPIServer_xauth')
            xauthfile = tempfile.NamedTemporaryFile(dir=xauth_dir)
            cookie = gen_xauth_cookie()

            try:
                run_xauth_xvfb(xauth_dir, xauthfile, self.__virtual_frame_buffer_port,
                               cookie)
                os.environ['DISPLAY'] = self.__virtual_frame_buffer_port
                casalog.post("Deployed virtual frame buffer at port {0} with PID {1}".
                             format(self.__virtual_frame_buffer_port,
                                    str(self.__virtual_frame_buffer_process.pid)),
                             "INFO", casalog_call_origin)
            except Exception:
                self.__virtual_frame_buffer_process = None                
                formatted_traceback = traceback.format_exc()
                casalog.post("Exception deploying virtual frame buffer at %s: %s" 
                             % (self.__virtual_frame_buffer_port,
                                str(formatted_traceback)),
                             "SEVERE",casalog_call_origin)
                
                
        def signal_stop_virtual_frame_buffer(self):
            
            casalog_call_origin = "MPICommandServer::signal_stop_virtual_frame_buffer"
            
            if self.__virtual_frame_buffer_process is not None:
                try:
                    self.__virtual_frame_buffer_process.terminate()
                    casalog.post("Virtual frame buffer deployed at %s with pid %s successfully shutdown" % 
                                 (self.__virtual_frame_buffer_port,
                                  str(self.__virtual_frame_buffer_process.pid)),
                                 "DEBUG",casalog_call_origin)
                    self.__virtual_frame_buffer_process = None
                except:
                    formatted_traceback = traceback.format_exc()
                    casalog.post("Exception shutting down virtual frame buffer deployed at %s with pid %s: %s" 
                                 % (self.__virtual_frame_buffer_port,
                                    str(self.__virtual_frame_buffer_process.pid),
                                    str(formatted_traceback)),
                                    "SEVERE",casalog_call_origin)
            else:
                casalog.post("Virtual frame buffer (port {0}) not deployed".
                             format(self.__virtual_frame_buffer_port), "WARN",
                             casalog_call_origin)

        def signal_stop_service_request(self):
            self.__stop_service_requested = True

        def omp_set_num_threads(self,omp_num_threads):
            
            casalog_call_origin = "MPICommandServer::omp_set_num_threads"

            try:
                current_omp_num_threads = casalog.ompGetNumThreads()
                casalog.post("Changing OpenMP number of threads from %s to %s" 
                             % (str(current_omp_num_threads),str(omp_num_threads)),
                             "INFO",casalog_call_origin)
                casalog.ompSetNumThreads(omp_num_threads)
                current_omp_num_threads = casalog.ompGetNumThreads()
                if current_omp_num_threads == omp_num_threads:
                    casalog.post("OpenMP number of threads successfully set to %s" 
                                 % str(current_omp_num_threads),
                                 "INFO",casalog_call_origin)
                else:
                    casalog.post("Error changing OpenMP number of threads, returned setting is %s" 
                                 % str(current_omp_num_threads),
                                 "SEVERE",casalog_call_origin)
            except:           
                formatted_traceback = traceback.format_exc()
                casalog.post("Exception Changing OpenMP number of threads: %s" % 
                             str(formatted_traceback),"SEVERE",casalog_call_origin)
                
            
        def start_services(self):
        
            self.__monitor_server.start_services()
            self.__start_command_request_handler_service()
            self.start_virtual_frame_buffer()
        
        
        def stop_services(self,force_command_request_interruption=False):

            if self.__logfile_descriptor is not None:
                 self.__logfile_descriptor.close()
                 self.__logfile_descriptor = None
                 
            self.__monitor_server.stop_services()
            
            if not force_command_request_interruption:
                self.__stop_command_request_handler_service()
            
        def serve(self):
            
            casalog_call_origin = "MPICommandServer::serve"        
            
            # First start command and ping status services
            casalog.post("Starting services...","INFO",casalog_call_origin) 
            self.start_services()
            
            # Notify to MPICommandClient that service is up and running
            self.__communicator.control_service_response_send(response=self.__monitor_server.get_status())
            
            # Keep serving until a stop signal service is received
            control_service_request = {}
            self.__stop_service_requested = False
            while ((not self.__stop_service_requested) and
                   (not self.__monitor_server.get_client_timeout())):
                # Check if there is an incoming control service msg
                msg_available = False
                try:
                    msg_available = self.__communicator.control_service_request_probe()
                except:
                    msg_available = False
                    formatted_traceback = traceback.format_exc()
                    casalog.post("Exception checking if control service msg is available: %s" 
                                 % str(formatted_traceback),"SEVERE",casalog_call_origin)                        
                
                # Notify to MPICommandClient that control signal has been processed
                if msg_available:
                    
                    # Receive control service msg
                    msg_received = False                    
                    control_service_request = {}
                    try:
                        control_service_request = self.__communicator.control_service_request_recv()
                        msg_received = True
                    except:
                        msg_received = False
                        formatted_traceback = traceback.format_exc()
                        casalog.post("Exception receiving control service msg: %s"
                                     % str(formatted_traceback),"SEVERE",casalog_call_origin)
                        continue

                    # Process control service msg
                    cmd = None
                    send_response = False
                    if msg_received:
                        try:
                            cmd = control_service_request['command']
                            send_response = control_service_request['send_response']
                            code = compile(cmd, casalog_call_origin, 'exec')
                            exec(code)
                            casalog.post("Control signal %s successfully handled by server %s" 
                                         % (str(cmd),str(MPIEnvironment.mpi_processor_rank)),
                                         "INFO",casalog_call_origin)
                        except:
                            formatted_traceback = traceback.format_exc()
                            casalog.post("Exception handling control signal command %s in server %s: %s" 
                                         % (str(control_service_request),
                                            str(MPIEnvironment.mpi_processor_rank),
                                            str(formatted_traceback)),
                                         "SEVERE",casalog_call_origin)

                    # Notify to MPICommandClient that control signal has been processed
                    if send_response:
                        try:
                            self.__communicator.control_service_response_send(response=self.__monitor_server.get_status())
                        except:
                            formatted_traceback = traceback.format_exc()
                            casalog.post("Exception sending response to control signal command %s in server %s: %s" 
                                         % (str(cmd),str(MPIEnvironment.mpi_processor_rank),str(formatted_traceback)),
                                         "SEVERE",casalog_call_origin)
                    
                time.sleep(MPIEnvironment.mpi_stop_service_sleep_time)
            
            # Process stop service request
            if self.__stop_service_requested:
                
                # Check if force mode is needed
                force_command_request_interruption = control_service_request['force_command_request_interruption']
                finalize_mpi_environment = control_service_request['finalize_mpi_environment']
                busy = self.__monitor_server.get_status('busy')
                if force_command_request_interruption and busy:
                    casalog.post("force-stop service signal received, stopping services, " + 
                                 "command request handler service will be interrupted...","INFO",casalog_call_origin)
                else:
                    force_command_request_interruption = False
                    casalog.post("stop service signal received, stopping services...","INFO",casalog_call_origin)
            else:
                force_command_request_interruption = True
                casalog.post("client timeout, forcing disconnection, " +
                             "command request handler service will be interrupted.." ,"INFO",casalog_call_origin)

            # Stop services
            self.stop_services(force_command_request_interruption)

            # Finalize MPI environment   
            if finalize_mpi_environment:    
                try:
                    casalog.post("Going to finalize MPI environment","INFO",casalog_call_origin)
                    MPIEnvironment.finalize_mpi_environment()
                except:
                    formatted_traceback = traceback.format_exc()
                    casalog.post("Exception finalizing MPI environment %s" 
                                 % str(formatted_traceback),"SEVERE",casalog_call_origin)

            # Exit
            casalog.post("Exiting", "INFO", casalog_call_origin)

        
# EOF
