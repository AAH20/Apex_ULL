#!/usr/bin/env python3
"""Execute a native in-memory queue probe and retain an Apex evidence envelope."""
import argparse
import hashlib
import json
import math
import os
import platform
import shlex
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def dump(path,data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--iterations',type=int,default=10000)
    parser.add_argument('--warmup',type=int,default=1000)
    parser.add_argument('--batch-size',type=int,default=1024)
    args=parser.parse_args(argv)
    if not 0<args.batch_size<=65536:
        parser.error('invalid batch size')
    if not 0<args.iterations<=10000000 or not 0<=args.warmup<=10000000:
        parser.error('invalid iteration/warmup bound')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('output must be absent or empty to preserve prior evidence')
    compiler=shlex.split(os.getenv('CC','cc'))
    flags=['-std=c11','-D_POSIX_C_SOURCE=200809L','-O2','-pthread']
    if os.getenv('SDKROOT') and platform.system()=='Darwin': flags+=['-isysroot',os.environ['SDKROOT']]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip())
    sources=['benchmarks/native_queue_probe.c','kernels/queue/queue.c','kernels/queue/queue.h']
    with tempfile.TemporaryDirectory() as temp:
        executable=Path(temp)/'probe'
        subprocess.run(compiler+flags+[str(ROOT/sources[0]),str(ROOT/sources[1]),'-o',str(executable)],check=True)
        data=json.loads(subprocess.check_output([str(executable),str(args.iterations),str(args.warmup),str(args.batch_size)],text=True))
        build={'compiler_version':subprocess.check_output(compiler+['--version'],text=True).splitlines()[0],
            'flags':[Path(f).name if f.startswith('/') else f for f in flags], 'sources':{p:sha(ROOT/p) for p in sources},'executable_sha256':sha(executable)}
    if len(data['samples'])!=args.iterations or data['elapsed_ns']<=0: raise ValueError('invalid native run')
    output=args.output;output.mkdir(parents=True,exist_ok=True)
    config={'capacity':1024,'payload':'pointer to constant unsigned 42','iterations':args.iterations,'warmup':args.warmup,'batch_size':args.batch_size,'build':build}
    spec={'id':'apex.ull.spsc.roundtrip','version':'0.1.0','boundary':'CLOCK_MONOTONIC before push to after pop and pointer correctness check','queue':'single producer and consumer on one thread','capacity':1024,'batch_size':args.batch_size,'payload':'constant unsigned 42 pointer'}
    cpu=platform.processor() or platform.machine()
    if platform.system()=='Darwin':
        identification=subprocess.run(['sysctl','-n','machdep.cpu.brand_string'],capture_output=True,text=True)
        cpu=identification.stdout.strip() if identification.returncode==0 else 'unknown ('+platform.machine()+')'
    inventory={'os':platform.system(),'os_version':platform.release(),'architecture':platform.machine(),'cpu':cpu,'logical_cpus':os.cpu_count(),'nic':'not used','affinity':'not pinned','power_policy':'not controlled'}
    files={'config.json':config,'workload.json':spec,'input.json':{'payload':42,'iterations':args.iterations,'batch_size':args.batch_size},'inventory.json':inventory,'build.json':build,'clock.json':{'name':'CLOCK_MONOTONIC','declared_resolution_ns':data['clock_resolution_ns'],'calibrated_uncertainty_ns':None},'schedule.json':{'mode':'closed_loop_sequential','warmup':args.warmup,'measurement_iterations':args.iterations,'batch_size':args.batch_size},'samples.json':data['samples'],'throughput.json':{'elapsed_ns':data['elapsed_ns'],'completed_count':args.iterations,'population':f'completed batches of {args.batch_size} sequential in-memory SPSC round trips'}}
    for name,value in files.items():dump(output/name,value)
    role={'throughput.json':'throughput_accounting','samples.json':'chronological_latency_samples_ns','inventory.json':'platform_inventory','build.json':'implementation'}
    artifacts=[{'id':name.removesuffix('.json'),'role':role.get(name,'configuration'),'location':name,'sha256':sha(output/name),'visibility':'public'} for name in files]
    samples=sorted(data['samples'])
    metrics=[]
    for statistic,prob in [('p50',.5),('p99',.99),('p99.9',.999),('p99.99',.9999)]:
        metrics.append({'id':'spsc.batch.'+statistic,'value':samples[max(0,math.ceil(prob*len(samples))-1)],'unit':'ns','statistic':statistic,'population':f'completed batches of {args.batch_size} sequential in-memory SPSC round trips','direction':'lower'})
    metrics.append({'id':'spsc.batch.rate','value':args.iterations/(data['elapsed_ns']/1e9),'unit':'events/s','statistic':'rate','population':f'completed batches of {args.batch_size} sequential in-memory SPSC round trips','direction':'higher'})
    record={'schema_version':'0.1.0','run_id':'apex-ull-host-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),'status':'valid','claim_kind':'measured',
        'provenance':{'repository_url':'https://github.com/AAH20/Apex_ULL','commit':commit,'dirty':dirty,'config_sha256':sha(output/'config.json'),'recorded_at':datetime.now(timezone.utc).isoformat(),'sources':[]},
        'workload':{'id':spec['id'],'version':'0.1.0','kind':'open','spec_sha256':sha(output/'workload.json'),'input_sha256':sha(output/'input.json'),'rights':'public_redistributable','semantics':spec['boundary'],'frame_integrity_policy':'not_applicable'},
        'platform':{'inventory_artifact':'inventory','implementation_artifact':'build','transport_backend':'in_memory_spsc','backend_status':'simulated'},
        'evidence':{'implementation':'software','environment':'cpu','validation':'none','validation_receipt':None},
        'measurement':{'method':'software_clock','start_boundary':'before first SPSC push of batch','stop_boundary':'after last SPSC pop and pointer check of batch','clock_artifact':'clock','calibration_artifact':None,'resolution_ns':max(1,data['clock_resolution_ns']),'uncertainty_artifact':None,'warmup_policy':f'exclude first {args.warmup} batches','sampling_policy':'all measured iterations in chronological order; nearest-rank quantiles','sample_count':args.iterations},
        'traffic':{'schedule_artifact':'schedule','offered_count':args.iterations,'accepted_count':args.iterations,'completed_count':args.iterations,'rejected_count':0,'dropped_count':0,'duplicate_output_count':0,'wrong_output_count':0,'unresolved_count':0},
        'metrics':metrics,'artifacts':artifacts,'limitations':['Host software-clock batch durations, not individual-operation, network or tick-to-trade latency.','Timer, loop and correctness-check overhead are included; CPU placement and power policy are uncontrolled.','Declared clock resolution is not calibrated uncertainty; finite samples do not establish a global latency bound.','Build recipe and binary digest are retained; binary replay requires rebuilding the identified source and toolchain.','No independent validation or official STAC execution.']}
    dump(output/'run.json',record)
    print(json.dumps({'record':str(output/'run.json'),'run_id':record['run_id'],'metrics':metrics},indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
