"""Opt-in, read-only fatal-dialog probe. No Win32 calls or DLL loads on import."""
import ctypes as C
import hashlib
import json
import ntpath
import os
from pathlib import Path
import sys
import time

TEXT_LIMIT = 16*1024
CONTROL_LIMIT = 8
MESSAGE_TIMEOUT_MS = 200
RECORD_LIMIT = 64*1024
CALLBACK = getattr(C, 'WINFUNCTYPE', C.CFUNCTYPE)(C.c_int, C.c_void_p, C.c_ssize_t)


class BasicInformation(C.Structure):
    _fields_ = [('exit_status',C.c_int32),('peb',C.c_void_p),
                ('affinity',C.c_size_t),('priority',C.c_int32),
                ('pid',C.c_size_t),('parent_pid',C.c_size_t)]


class Win32Reader:
    """Existing Python ctypes only; original process handles are never closed."""
    def __init__(self):
        if os.name != 'nt' or C.sizeof(C.c_void_p) != 8:
            raise OSError('Pinned Windows x64 interpreter required')
        self.kernel=C.WinDLL('kernel32',use_last_error=True)
        self.user=C.WinDLL('user32',use_last_error=True)
        self.nt=C.WinDLL('ntdll',use_last_error=True)
        signatures = [
            (self.kernel,'GetCurrentProcess',C.c_void_p,[]),
            (self.kernel,'GetProcessId',C.c_uint32,[C.c_void_p]),
            (self.kernel,'WaitForSingleObject',C.c_uint32,[C.c_void_p,C.c_uint32]),
            (self.kernel,'GetProcessTimes',C.c_int,[C.c_void_p]+[C.POINTER(C.c_uint64)]*4),
            (self.kernel,'QueryFullProcessImageNameW',C.c_int,[C.c_void_p,C.c_uint32,C.c_wchar_p,C.POINTER(C.c_uint32)]),
            (self.nt,'NtQueryInformationProcess',C.c_int32,[C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32,C.POINTER(C.c_uint32)]),
            (self.user,'EnumWindows',C.c_int,[CALLBACK,C.c_ssize_t]),
            (self.user,'EnumChildWindows',C.c_int,[C.c_void_p,CALLBACK,C.c_ssize_t]),
            (self.user,'GetWindowThreadProcessId',C.c_uint32,[C.c_void_p,C.POINTER(C.c_uint32)]),
            (self.user,'GetWindowTextW',C.c_int,[C.c_void_p,C.c_wchar_p,C.c_int]),
            (self.user,'GetClassNameW',C.c_int,[C.c_void_p,C.c_wchar_p,C.c_int]),
            (self.user,'IsChild',C.c_int,[C.c_void_p,C.c_void_p]),
            (self.user,'SendMessageTimeoutW',C.c_ssize_t,[C.c_void_p,C.c_uint32,C.c_size_t,C.c_void_p,C.c_uint32,C.c_uint32,C.POINTER(C.c_size_t)])]
        for library,name,result,args in signatures:
            method=getattr(library,name);method.restype=result;method.argtypes=args

    def current_handle(self):
        return self.kernel.GetCurrentProcess()

    def identity(self, handle):
        if self.kernel.WaitForSingleObject(handle,0) != 258:
            raise OSError('Original process exited or handle unavailable')
        pid=self.kernel.GetProcessId(handle)
        created,exited,kernel,user=(C.c_uint64() for _ in range(4))
        if not pid or not self.kernel.GetProcessTimes(handle,C.byref(created),C.byref(exited),C.byref(kernel),C.byref(user)):
            raise OSError('Original process times unavailable')
        image=C.create_unicode_buffer(32768);size=C.c_uint32(len(image))
        if not self.kernel.QueryFullProcessImageNameW(handle,0,image,C.byref(size)):
            raise OSError('Original process image unavailable')
        basic=BasicInformation();returned=C.c_uint32()
        status=self.nt.NtQueryInformationProcess(handle,0,C.byref(basic),C.sizeof(basic),C.byref(returned))
        if status != 0 or returned.value != C.sizeof(basic) or basic.pid != pid:
            raise OSError('Original parent identity unavailable')
        return {'pid':pid,'parent_pid':basic.parent_pid,'created_filetime':created.value,'image':image.value}

    def window_owner(self, hwnd):
        pid=C.c_uint32()
        if not hwnd or not self.user.GetWindowThreadProcessId(hwnd,C.byref(pid)):
            raise OSError('Window ownership unavailable')
        return pid.value

    def windows(self, pid):
        found=[];visited=0;errors=[]
        @CALLBACK
        def callback(hwnd, unused):
            nonlocal visited
            try:
                visited+=1
                if self.window_owner(hwnd)==pid: found.append(int(hwnd))
            except BaseException as error: errors.append(type(error).__name__)
            return visited < 256 and len(found) < 8
        self.user.EnumWindows(callback,0)
        if errors: raise OSError('Window ownership changed during enumeration')
        return found

    def caption(self, hwnd):
        value=C.create_unicode_buffer(512)
        self.user.GetWindowTextW(hwnd,value,len(value))
        return value.value

    def class_name(self, hwnd):
        value=C.create_unicode_buffer(256)
        if not self.user.GetClassNameW(hwnd,value,len(value)):
            raise OSError('Window class unavailable')
        return value.value

    def children(self, hwnd):
        if not hwnd: raise OSError('Root HWND required; desktop enumeration refused')
        result=[]
        @CALLBACK
        def callback(child, unused):
            result.append(int(child))
            return len(result) < CONTROL_LIMIT
        self.user.EnumChildWindows(hwnd,callback,0)
        return result

    def is_child(self, root, child):
        return bool(self.user.IsChild(root,child))

    def static_text(self, hwnd):
        value=C.create_unicode_buffer(2048);result=C.c_size_t()
        C.set_last_error(0)
        # Only WM_GETTEXT; no broadcast, command, click or window mutation.
        ok=self.user.SendMessageTimeoutW(hwnd,0x000D,len(value),C.cast(value,C.c_void_p),
                                        0x0002|0x0020,MESSAGE_TIMEOUT_MS,C.byref(result))
        if not ok: raise OSError(f'WM_GETTEXT failed or timed out ({C.get_last_error()})')
        return value.value


def same_identity(actual, expected):
    return (actual['pid']==expected['pid'] and actual['parent_pid']==expected['parent_pid']
            and actual['created_filetime']==expected['created_filetime']
            and ntpath.normcase(actual['image'])==ntpath.normcase(expected['image']))


class FatalDialogProbe:
    def __init__(self, api, handle, pid, image, expected_sha, parent_image,
                 digest=None, clock=time.monotonic):
        self.api=api;self.handle=handle;self.clock=clock;self.done=False
        self.digest=digest or (lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest())
        self.expected_sha=expected_sha;self.parent_handle=api.current_handle()
        self.parent=api.identity(self.parent_handle);self.child=api.identity(handle)
        if (self.child['pid']!=pid or self.child['parent_pid']!=self.parent['pid']
            or self.parent['pid']!=os.getpid() or self.child['created_filetime']<self.parent['created_filetime']
            or ntpath.normcase(self.child['image'])!=ntpath.normcase(str(image))
            or ntpath.normcase(self.parent['image'])!=ntpath.normcase(parent_image)):
            raise OSError('Original parent/child identity differs')
        self._verify()

    def _verify(self, hwnd=None):
        if (not same_identity(self.api.identity(self.handle),self.child)
            or not same_identity(self.api.identity(self.parent_handle),self.parent)):
            raise OSError('Original process identity changed')
        if hwnd is not None and self.api.window_owner(hwnd)!=self.child['pid']:
            raise OSError('Fatal HWND was reassigned')

    def poll(self):
        if self.done: return None
        self._verify()
        for hwnd in self.api.windows(self.child['pid']):
            self._verify(hwnd)
            caption=self.api.caption(hwnd)
            self._verify(hwnd)
            if caption.casefold()=='fatal error':
                self.done=True
                return self.capture(hwnd,caption)
        return None

    def capture(self, hwnd, caption):
        record={'schema':'iw7.recipient-fatal-dialog/1','fatal_window_observed':True,
                'identity_verified_after':False,'identity':self.child,'parent':self.parent,
                'hwnd':hwnd,'title':None,'class':None,'controls':[],'text_bytes':0,'errors':[],
                'text_truncated':False,'control_limit':CONTROL_LIMIT,'text_limit':TEXT_LIMIT,
                'message_timeout_ms':MESSAGE_TIMEOUT_MS,'whole_capture_deadline_guaranteed':False,
                'DirectJobMembershipQueried':False,'interaction_performed':False}
        def take(value):
            raw=value.encode('utf-8','replace');remaining=TEXT_LIMIT-record['text_bytes']
            selected=raw[:remaining].decode('utf-8','ignore')
            record['text_bytes']+=len(selected.encode('utf-8'))
            record['text_truncated'] |= len(raw)>remaining
            return selected
        try:
            self._verify(hwnd)
            if self.digest(self.child['image'])!=self.expected_sha: raise OSError('E7 hash changed')
            record['title']=take(caption);record['class']=take(self.api.class_name(hwnd))
            deadline=self.clock()+2.0
            for child in self.api.children(hwnd)[:CONTROL_LIMIT]:
                if self.clock()>=deadline or record['text_bytes']>=TEXT_LIMIT:
                    record['text_truncated']=True;break
                self._verify(hwnd)
                if self.api.window_owner(child)!=self.child['pid'] or not self.api.is_child(hwnd,child):
                    raise OSError('Child control ownership changed')
                kind=self.api.class_name(child);text='';error=None
                if kind.casefold()=='static':
                    try: text=self.api.static_text(child)
                    except OSError as failure: error=str(failure)[:160]
                if self.api.window_owner(child)!=self.child['pid'] or not self.api.is_child(hwnd,child):
                    raise OSError('Child control reassigned during read')
                record['controls'].append({'hwnd':child,'class':take(kind),'text':take(text),'error':error})
            self._verify(hwnd)
            if self.digest(self.child['image'])!=self.expected_sha: raise OSError('E7 hash changed after read')
            record['identity_verified_after']=True
        except BaseException as error:
            # Discard potentially misattributed text after any identity failure.
            record.update(title=None,**{'class':None},controls=[],text_bytes=0)
            record['errors'].append(type(error).__name__)
        return record


def make_probe(process, image, expected_sha):
    return FatalDialogProbe(Win32Reader(),int(process._handle),process.pid,image,expected_sha,sys.executable)


def save_record(path, record):
    payload=(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if len(payload)>RECORD_LIMIT: raise OSError('Fatal dialog record exceeds64KiB')
    with Path(path).open('x',encoding='utf-8',newline='\n') as output:
        output.write(payload.decode('utf-8'))
