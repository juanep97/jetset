
__author__ = "Andrea Tramacere"




# on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

# if on_rtd == True:
#     try:
#         from .jetkernel import jetkernel as BlazarSED
#     except ImportError:
#         from .mock import jetkernel as BlazarSED
# else:

from .jetkernel import jetkernel as BlazarSED

import  warnings
import numpy as np
import time
import  ast
import copy
import dill as pickle


from tqdm.autonotebook import tqdm

import threading

from astropy import constants as const

from .model_parameters import _show_table
from .jet_model import  Jet

from astropy.table import Table
from astropy.units import Unit


from .jet_paramters import JetModelDictionaryPar,JetParameter,JetModelParameterArray
from .jet_emitters import  ArrayDistribution, EmittersArrayDistribution

from .model_manager import FitModel

from .plot_sedfit import  BasePlot,PlotPdistr,PlotTempEvDiagram,PlotTempEvEmitters, PlotSED


__all__=['JetTimeEvol']


class ProgressBarTempEV(object):

    def __init__(self, target_class,N):
        self.target_class = target_class
        self.N = N
        self.pbar = tqdm(total=self.N)


        self.stop = False
        self.pbar.n=0

    def update(self):
        step_tqdm = self.target_class.temp_ev.T_COUNTER +1 - self.pbar.n
        self.pbar.update(step_tqdm)

    def finalzie(self,max_try=10):
        n_try=1
        while (self.pbar.n<self.N and n_try<max_try):
            time.sleep(.1)
            n_try += 1
            self.update()
        self.pbar.display()

    def run(self):
        self.pbar.n = 0
        while (self.stop is False):
            self.update()
            time.sleep(.1)

class TimeEmittersDistribution(object):

    def __init__(self,time_size,gamma_size):
        self.time=np.zeros(time_size)
        self.gamma=np.zeros(gamma_size)
        self.n_gamma_rad = np.zeros((time_size,(gamma_size)))
        self.n_gamma_acc = np.zeros((time_size, (gamma_size)))

    def _get_time_slice_samples(self, time,time_bin=None):
        if time > self.time[-1] or time < self.time[0]:

            warnings.warn('time must be within time start/stop range', self.time[0], self.time[-1])
            return None
        #dt = (self.N_time[-1]-self.N_time[0])/self.self.N_time.size
        #id = np.int(time/dt)

        ID=[np.argmin(np.fabs(self.time-time))]
        if time_bin is not None:
            ID_l = np.argwhere(np.logical_and(self.time >= time, self.time <= time+time_bin ))
            if len(ID_l) > 0:
                ID = ID_l.ravel()

        return ID



class TimeSEDs(object):

    def __init__(self,temp_ev,build_cached=True):
        self.temp_ev=temp_ev
        self.num_seds=temp_ev.parameters.num_samples.val
        self.seds_array=None
        self.time_array=np.zeros( self.num_seds, dtype=np.double)
        if build_cached is True:
            self.build_cached_SEDs()

    def get_SED(self, comp, time_slice=None, time=None, time_bin=None):

        if time_slice is None:
            time_samples = self.temp_ev.time_sampled_emitters._get_time_slice_samples(time,time_bin=time_bin)
        else:
            time_samples = [time_slice]

        selected_seds_list=[]
        if time_bin is None:
            pass
        for ts in time_samples:
            #print(ts)
            selected_seds_list.append([sed for sed in self.seds_array[ts] if sed.name == comp][0])

        sed=None

        if len(selected_seds_list) == 1:
            sed = selected_seds_list[0]
        else:
            sed=copy.deepcopy(selected_seds_list[0])

            for ID in range(len(selected_seds_list)):
                sed._nuFnu += selected_seds_list[ID]._nuFnu

            sed._nuFnu *= 1.0/len(selected_seds_list)

        return sed

    def build_cached_SEDs(self):
        print('caching SED for each saved distribution: start')
        self.seds_array = [None ] * self.num_seds
        pbar = tqdm(total=self.num_seds)
        pbar.n = 0
        for T in range(self.num_seds):
            self.temp_ev.set_time(time_slice=T)
            self.temp_ev.jet_rad.eval()
            self.seds_array[T] = [copy.deepcopy(s.SED) for s in self.temp_ev.jet_rad.spectral_components_list]
            pbar.update(1)
        pbar.display()
        print('caching SED for each saved distribution: done')

class JetTimeEvol(object):
    """


        Parameters
        ----------
        jet
        Q_inj
        name
        inplace
        jet_gamma_grid_size
        log_sampling




        The model parameters can be set after object creation, eg:

        .. code-block:: python

            from jetset.jet_emitters_factory import EmittersFactory
            q_inj=InjEmittersFactory().create_inj_emitters('pl',emitters_type='electrons',normalize=True)
            q_inj.parameters.gmax.val=5


            from jetset.jet_timedep import  JetTimeEvol
            from jetset.jet_model import Jet

            my_jet=Jet()

            temp_ev_acc=JetTimeEvol(jet=my_jet_acc,Q_inj=q_inj,inplace=True)

            temp_ev_acc.parameters.duration.val=1E4


        model parameters
        ----------------
        duration: float (s)
            duration of the evolution in seconds

        gmin_grid: float
            lower bound of the gamma grid for the temporal evolution

        gmax_grid: float
            upper bound of the gamma grid for the temporal evolution

        gamma_grid_size: int
            size of the gamma grid

        TStart_Acc: float (s)
            starting time of the acceleration process

        TStop_Acc: float (s)
            stop time of the acceleration process

        TStart_Inj: float (s)
            starting time of the injection process

        TStop_Inj: float (s)
            stop time of the injection process

        T_esc: float (R/c)
            escape time scale in  (R/c)

        Esc_Index: float
            power-law index for the escapce term t_esc(gamma)=T_esc*gamma^(Esc_Index)

        t_D0: float (s)
            acceleration time scale for diffusive acceleration term

        t_A0: float (s)
            acceleration time scale for the systematic acceleration term

        Diff_Index: float (s)
            power-law index for the diffusive acceleration term

        Acc_Index: float (s)
            power-law index for the systematic acceleration term

        Lambda_max_Turb: float (cm)
            max scale of the turbulence

        Lambda_choer_Turb_factor: float (cm)
           max scale   for the quasi-linear resonant regime

        t_size: int
            number of steps for the time grid

        num_samples: int
            number of the time steps saved in the output

        L_inj: float (erg/s)
            if not None, the inj function is rescaled to match L_inj
    """

    def __init__(self,
                 jet_rad,
                 Q_inj=None,
                 #flag='tests',
                 name='jet_time_ev',
                 inplace=True,
                 log_sampling=False,
                 jet_gamma_grid_size=200):


        self._temp_ev = BlazarSED.MakeTempEv()

        if inplace is True:
            self.jet_rad=jet_rad.clone()
        else:
            self.jet_rad=jet_rad


        self._jet_acc = copy.deepcopy(self.jet_rad)
        self._jet_acc.name=self.jet_rad.name+'acc_region'

        self._m = FitModel()
        self._m.add_component(self.jet_rad)
        self._m.add_component(self._jet_acc)
        self._m.parameters.link_par('z_cosm',[self._jet_acc.name],self.jet_rad.name)

        self.Q_inj=Q_inj
        self.name=name

        self.parameters = JetModelParameterArray(model=self)
        temp_ev_dict,jet_acc_dict = self._build_par_dict()
        self.parameters.add_par_from_dict(temp_ev_dict,self,'_temp_ev',JetParameter)
        self._jet_acc.parameters.B.name='B_acc'
        self._jet_acc.parameters.B.val=1.0
        self.parameters.add_par(self._jet_acc.parameters.B)
        self._jet_acc.parameters.R.name = 'R_acc'
        self._jet_acc.parameters.R.val = self.jet_rad.parameters.R.val/10
        self.parameters.add_par(self._jet_acc.parameters.R)
        self.jet_gamma_grid_size = jet_gamma_grid_size

        self._cached_SEDs = None

        self._custom_q_jnj_profile=None
        self._custom_acc_profile = None
        self.time_steps_array = None
        self.IC_cooling = 'off'
        self.Sync_cooling = 'on'
        self.log_sampling = log_sampling
        self.time_sampled_emitters = None
        #self.N_time = None
        #self.gamma = None
        #self.N_gamma = None


    def save_model(self, file_name):

        pickle.dump(self, open(file_name, 'wb'), protocol=pickle.HIGHEST_PROTOCOL)


    @classmethod
    def load_model(cls, file_name):
        try:
            c = pickle.load(open(file_name, "rb"))
            c.init_TempEv()
            return c
        except Exception as e:
            raise RuntimeError(e)

    @property
    def time_steps_array(self):
        return self._time_steps_array

    @time_steps_array.setter
    def time_steps_array(self,v):
        self._time_steps_array = v

    @property
    def temp_ev(self):
        return self._temp_ev

    def show_pars(self, sort_key='par type'):
        self.parameters.show_pars(sort_key=sort_key)

    def init_TempEv(self):
        BlazarSED.Init(self.jet_rad._blob, self.jet_rad.get_DL_cm())
        #if self.jet_acc is not None:
        BlazarSED.Init(self._jet_acc._blob, self._jet_acc.get_DL_cm())
        self._init_temp_ev()
        self._set_inj_time_profile(user_defined_array=self._custom_q_jnj_profile)
        self._set_acc_time_profile(user_defined_array=self._custom_acc_profile)
        self._fill_temp_ev_array_pre_run()

        self._build_tempev_table(self.jet_rad, self._jet_acc)


    def run(self,only_injection=True, cache_SEDs=True):
        self.cache_SEDs=cache_SEDs
        print('temporal evolution running')
        self.init_TempEv()
        pbar=ProgressBarTempEV(target_class=self, N=self.parameters.t_size.val)
        t1 = threading.Thread(target=pbar.run)
        t1.start()
        BlazarSED.Run_temp_evolution(self.jet_rad._blob, self._jet_acc._blob, self._temp_ev, int(only_injection))
        pbar.stop = True
        pbar.finalzie()
        self._fill_temp_ev_array_post_run()
        print('temporal evolution completed')

        self._set_jet_post_run()
        if cache_SEDs is True:
            self._cached_SEDs = TimeSEDs(temp_ev=self,build_cached=True)



    @property
    def log_sampling(self):
        """
        logarithmically spaced bool
        Returns
        -------

        """
        return self._log_sampling

    @log_sampling.setter
    def log_sampling(self, v):
        """
        if True, the time grid is logarithmically spaced
        Returns
        -------

        """
        if v is False or v is True:
            pass
        else:
            raise RuntimeError('this parameter must be bolean')

        self._log_sampling = v
        self.temp_ev.LOG_SET= np.int(v)

    @property
    def t_unit_rad(self):
        """
        blob time in R/c
        Returns
        -------

        """
        return self._temp_ev.t_unit_rad

    @property
    def t_unit_acc(self):
        """
        blob time in R/c
        Returns
        -------

        """
        return self._temp_ev.t_unit_acc

    @property
    def delta_t(self):
        """
        blob delta t in s
        Returns
        -------

        """
        return self._temp_ev.deltat


    @property
    def IC_cooling(self):
        return self._IC_cooling

    @IC_cooling.setter
    def IC_cooling(self, val):
        state_dict = dict((('on', 1), ('off', 0)))
        if val not in state_dict.keys():
            raise  RuntimeError('allowed values are on/off')
        self._IC_cooling=val
        self.temp_ev.do_Compton_cooling=state_dict[val]

    @property
    def Sync_cooling(self):
        return self._Sync_cooling

    @Sync_cooling.setter
    def Sync_cooling(self, val):
        state_dict = dict((('on', 1), ('off', 0)))
        if val not in state_dict.keys():
            raise RuntimeError('allowed values are on/off')
        self._Sync_cooling = val
        self.temp_ev.do_Sync_cooling = state_dict[val]


    @property
    def custom_q_jnj_profile(self):
        return self._custom_q_jnj_profile

    @custom_q_jnj_profile.setter
    def custom_q_jnj_profile(self,user_defined_array):
        self._set_inj_time_profile(user_defined_array)

    @property
    def custom_acc_profile(self):
        return self._custom_acc_profile

    @custom_acc_profile.setter
    def custom_acc_profile(self, user_defined_array):
        self._set_acc_time_profile(np.double(user_defined_array>0))

    def _set_inj_time_profile(self,user_defined_array=None):
        if user_defined_array is None:
            self._custom_q_jnj_profile = np.zeros(self.parameters.t_size.val, dtype=np.double)
            msk= self.time_steps_array > self._temp_ev.TStart_Inj
            msk*= self.time_steps_array < self._temp_ev.TStop_Inj
            self._custom_q_jnj_profile[msk] = 1.0
        else:
            if np.shape(user_defined_array)!=(self.parameters.t_size.val,):
                raise  RuntimeError('user_defined_array must be 1d array with size =',self._temp_ev.T_SIZE)
            self._custom_q_jnj_profile = np.double(user_defined_array)

    def _set_acc_time_profile(self,user_defined_array=None):
        if user_defined_array is None:
            self._custom_acc_profile = np.zeros(self._temp_ev.T_SIZE, dtype=np.double)
            msk= self.time_steps_array >= self._temp_ev.TStart_Acc
            msk*= self.time_steps_array <= self._temp_ev.TStop_Acc
            self._custom_acc_profile[msk] = 1.0
        else:
            if np.shape(user_defined_array)!=(self.parameters.t_size.val,):
                raise  RuntimeError('user_defined_array must be 1d array with size =',self._temp_ev.T_SIZE)
            self._custom_acc_profile = np.double(user_defined_array)


    def get_SED(self, comp, time_slice=None, time=None, use_cached=False, time_bin=None):
        if time_bin is None:
            pass
        else:
            pass

        if self._cached_SEDs is None or use_cached is False:
            self.set_time(time_slice=time_slice,time=time)
            self.jet_rad.eval()
            s = getattr(self.jet_rad.spectral_components, comp).SED
        else:
            s = self._cached_SEDs.get_SED(comp=comp, time_slice=time_slice,time=time, time_bin=time_bin)

        return s


    def _set_jet_post_run(self):
        self._jet_emitters_distr = EmittersArrayDistribution(name='time_dep',
                                                             gamma_array=np.copy(self.time_sampled_emitters.gamma),
                                                             n_gamma_array=np.copy(self.time_sampled_emitters.n_gamma_rad[-1]),
                                                             gamma_grid_size=self.jet_gamma_grid_size,
                                                             normalize=False)
        self._jet_emitters_distr._fill()
        self._jet_emitters_distr._fill()
        self.jet_rad.set_emitters_distribution(self._jet_emitters_distr)



    def _init_temp_ev(self):
        self.time_steps_array = np.linspace(0., self._temp_ev.duration, self.parameters.t_size.val, dtype=np.double)
        if self.Q_inj is not None:
            setattr(self._temp_ev,'Q_inj_jetset_gamma_grid_size',self.Q_inj._gamma_grid_size)
        BlazarSED.Init_Q_inj(self._temp_ev)
        BlazarSED.Init_temp_evolution(self.jet_rad._blob, self._jet_acc._blob, self._temp_ev, self.jet_rad.get_DL_cm())
        if self.Q_inj is not None:
            self.Q_inj._set_L_inj(self.parameters.L_inj.val,BlazarSED.V_sphere(self.parameters.R_acc.val))
            Ne_custom_ptr = getattr(self._temp_ev, 'Q_inj_jetset')
            gamma_custom_ptr = getattr(self._temp_ev, 'gamma_inj_jetset')
            for ID in range(self.Q_inj._gamma_grid_size):
                BlazarSED.set_q_inj_user_array(gamma_custom_ptr, self._temp_ev, self.Q_inj.gamma_e[ID], ID)
                BlazarSED.set_q_inj_user_array(Ne_custom_ptr, self._temp_ev, self.Q_inj.n_gamma_e[ID], ID)

    def _fill_temp_ev_array_pre_run(self):
        size = BlazarSED.static_ev_arr_grid_size
        self.gamma_pre_run=np.zeros(size)
        self.t_Sync_cool_pre_run = np.zeros(size)
        self.t_D_pre_run = np.zeros(size)
        self.t_DA_pre_run = np.zeros(size)
        self.t_A_pre_run = np.zeros(size)
        self.t_Esc_rad_pre_run = np.zeros(size)
        self.t_Esc_acc_pre_run = np.zeros(size)

        for i in range(size):
            self.gamma_pre_run[i] = BlazarSED.get_temp_ev_array_static(self._temp_ev.g, i)
            self.t_Sync_cool_pre_run[i] = BlazarSED.get_temp_ev_array_static(self._temp_ev.t_Sync_cool, i)
            self.t_D_pre_run[i] = BlazarSED.get_temp_ev_array_static(self._temp_ev.t_D, i)
            self.t_DA_pre_run[i] = BlazarSED.get_temp_ev_array_static(self._temp_ev.t_DA, i)
            self.t_A_pre_run[i] = BlazarSED.get_temp_ev_array_static(self._temp_ev.t_A, i)
            self.t_Esc_acc_pre_run[i] = BlazarSED.get_temp_ev_array_static(self._temp_ev.t_Esc_acc, i)
            self.t_Esc_rad_pre_run[i] = BlazarSED.get_temp_ev_array_static(self._temp_ev.t_Esc_rad, i)

        for i in range(self.parameters.t_size.val):
            T_inj_profile_ptr = getattr(self._temp_ev, 'T_inj_profile')
            BlazarSED.set_temp_ev_Time_array(T_inj_profile_ptr, self._temp_ev, self.custom_q_jnj_profile[i], i)
            Acc_profile_ptr = getattr(self._temp_ev, 'T_acc_profile')
            BlazarSED.set_temp_ev_Time_array(Acc_profile_ptr, self._temp_ev, self.custom_acc_profile[i], i)

    def eval_L_tot_inj(self):
        if self.Q_inj is not None and self._jet_acc is not None:
            return self.Q_inj.eval_U_q() * BlazarSED.V_sphere(self._jet_acc.parameters.R.val)



    def _get_time_slice_T_array(self, time):
        """
        Returns the time slice for a given time
        Parameters
        ----------
        time

        Returns
        -------

        """
        r = min(0, np.int(np.log10(self.delta_t))-1)
        if r<0:
            _time = np.round(time,-r)
        else:
            _time = time

        if _time > self.time_steps_array[-1] or _time < self.time_steps_array[0]:
            raise RuntimeError('time must be within time start/stop range', self.time_steps_array[0], self.time_steps_array[-1],'time=',_time)

        dt = (self.time_steps_array[-1] - self.time_steps_array[0]) / self.time_steps_array.size
        _id = np.int(_time/dt)

        if _id<0:
            _id =  0

        if _id > self.time_steps_array.size - 1:
            _id = self.time_steps_array.size - 1

        return _id


    def set_time(self,time_slice=None,time=None):
        if time_slice is None and time is None:
            raise RuntimeError('you can use either the N-th time slice, or the time in seconds')
        if time_slice is None:
            time_slice=self.time_sampled_emitters._get_time_slice_samples(time)[0]

        self.jet_rad.emitters_distribution._set_arrays(self.time_sampled_emitters.gamma, self.time_sampled_emitters.n_gamma_rad[time_slice].flatten())
        self.jet_rad.emitters_distribution._fill()


    def _fill_temp_ev_array_post_run(self):
        gamma_size = self._temp_ev.gamma_grid_size
        time_size = self.parameters.num_samples.val
        self.time_sampled_emitters=TimeEmittersDistribution(time_size=time_size, gamma_size=gamma_size)

        self.time_sampled_emitters.time = np.zeros(time_size)
        #self.gamma = np.zeros(gamma_size)
        #self.N_gamma = np.zeros((time_size,(gamma_size)))
        for i in range(time_size):
            self.time_sampled_emitters.time[i]=BlazarSED.get_temp_ev_N_time_array(self._temp_ev.N_time, self._temp_ev, i)
            for j in range(gamma_size):
                self.time_sampled_emitters.gamma[j] = BlazarSED.get_temp_ev_gamma_array(self._temp_ev.gamma, self._temp_ev, j)
                self.time_sampled_emitters.n_gamma_rad[i,j] = BlazarSED.get_temp_ev_N_gamma_array(self._temp_ev.N_rad_gamma, self._temp_ev,i,j)
                self.time_sampled_emitters.n_gamma_acc[i, j] = BlazarSED.get_temp_ev_N_gamma_array(self._temp_ev.N_acc_gamma,
                                                                                               self._temp_ev, i, j)

    def plot_time_profile(self,figsize=(8,8),dpi=120):
        p=PlotTempEvDiagram(figsize=figsize,dpi=dpi)
        p.plot(self.parameters.duration.val,
               self.time_steps_array,
               self.custom_q_jnj_profile,
               self.custom_acc_profile)
        return p

    def plot_TempEv_emitters(self,region='rad',figsize=(8,8),dpi=120,energy_unit='gamma',loglog=True,plot_Q_inj=True,pow=None):
        p=PlotTempEvEmitters(figsize=figsize,dpi=dpi,loglog=loglog)
        p.plot_distr(self,region=region,energy_unit=energy_unit,plot_Q_inj=plot_Q_inj,pow=pow)

        return p


    def plot_pre_run_plot(self,figsize=(8,6),dpi=120):
        p=BasePlot(figsize=figsize,dpi=dpi)
        p.ax.loglog(self.gamma_pre_run, self.t_Sync_cool_pre_run, label='t coool, synch.')
        p.ax.loglog(self.gamma_pre_run, self.t_D_pre_run, label='t acc. diffusive')
        p.ax.loglog(self.gamma_pre_run, self.t_DA_pre_run, label='t acc. diffusive syst.')
        p.ax.loglog(self.gamma_pre_run, self.t_A_pre_run, label='t acc. systematic')
        p.ax.loglog(self.gamma_pre_run, self.t_Esc_acc_pre_run, label='t esc R acc.')
        p.ax.loglog(self.gamma_pre_run, self.t_Esc_rad_pre_run, label='t esc R rad.')
        p.ax.axhline(self.delta_t, label='delta t', ls='--')
        p.ax.axvline(self._temp_ev.gamma_eq_t_A, ls='--')
        p.ax.axvline(self._temp_ev.gamma_eq_t_D, ls='--')

        p.ax.legend()
        return p

    def make_lc(self, nu1, nu2, comp='Sum', t1=None, t2=None, delta_t_out=None, n_slices=1000, rest_frame='obs', eval_cross_time=True, use_cached=False, R=None, name=None):
        if t1 is None:
            t1=self.time_sampled_emitters.time[0]
        if t2 is None:
            t2=self.time_sampled_emitters.time[-1]

        selected_time_slices = np.logical_and(self.time_sampled_emitters.time >= t1, self.time_sampled_emitters.time <= t2)

        if delta_t_out is None:
            time_array_out = self.time_sampled_emitters.time[selected_time_slices]
        else:
            time_array_out = np.arange(t1, t2, delta_t_out)

        time_array=self.time_sampled_emitters.time[selected_time_slices]
        flux_array=np.zeros(time_array.shape)

        for ID, time_slice in enumerate(np.argwhere(selected_time_slices).ravel()):
            s = self.get_SED(comp, time_slice=time_slice, use_cached=use_cached)
            if rest_frame=='src':
                msk = s.nu_src.value >= nu1
                msk *= s.nu_src.value <= nu2
                x = s.nu_src[msk]
                y = s.nuLnu_src[msk] / x
            elif rest_frame == 'obs':
                msk = s.nu.value >= nu1
                msk *= s.nu.value <= nu2
                x = s.nu[msk]
                y = s.nuFnu[msk] / x
            else:
                raise  RuntimeError('rest frame must be src or obs')
            flux_array[ID] = np.trapz(y.value, x.value)


        flux_array_out = np.interp(time_array_out,time_array, flux_array, left=0, right=0)

        if eval_cross_time is True:
            flux_array_out = self.eval_cross_time(time_array_out, flux_array_out, n_slices=n_slices, R=R)

        if rest_frame == 'src':
            beaming = self.jet_rad.get_beaming()
            z = 0
        else:
            beaming = self.jet_rad.get_beaming()
            z = self.jet_rad.parameters.z_cosm.val

        time_array_out = time_array_out*(1+z)/beaming
        return Table([time_array_out * Unit('s'), flux_array_out * Unit('erg s-1 cm-2')], names=('time', 'flux'), meta={'name': name})

    def _lc_weight(self, delay_r, R, delta_R):
        return 3*(R-delay_r)*(R+delay_r)*delta_R/(4*R*R*R)

    def eval_cross_time(self,t,lc,n_slices=1000,R=None):
        if R is None:
            R = self.jet_rad.parameters.R.val

        c = const.c.cgs.value

        delta_R = (2 * R) / n_slices
        delay_t = np.linspace(0, 2 * R / c, n_slices)
        delay_r = R - delay_t * c
        weight_array = self._lc_weight(delay_r, R, delta_R)
        lc_out = np.zeros(lc.shape)
        for ID, lc_in in enumerate(lc):
            t_interp = np.linspace(t[ID] - 2 * R / c, t[ID], n_slices)
            m = t_interp > t[0]
            lc_interp = np.interp(t_interp[m], t, lc,left=0, right=0)
            lc_out[ID] = np.sum(lc_interp * weight_array[m])

        return lc_out

    def plot_model(self, num_seds=None, time_slice=None, t1=None, t2=None,p=None,sed_data=None,comp='Sum', use_cached=False, time_bin=None):

        if t1 is None or t1<self.time_sampled_emitters.time[0]:
            t1=self.time_sampled_emitters.time[0]

        if t2 is None or t2>self.time_sampled_emitters.time[-1]:
            t2=self.time_sampled_emitters.time[-1]

        if time_bin is None:
            time_bin = self.time_sampled_emitters.time.size

        if num_seds is None:
            t_array = np.arange(t1, t2, time_bin)
        else:
            t_array = np.linspace(t1, t2, num_seds)

        if p is None:
            p = PlotSED()

        for ID, t in enumerate(t_array):
            #print(t1,t2,t)
            s = self.get_SED(comp, time=t, use_cached=use_cached, time_bin=time_bin)
            label = None
            ls = '-'
            color = 'r'
            if self.custom_q_jnj_profile[self._get_time_slice_T_array(t)] > 0:
                color = 'g'
                ls = '-'
                lw=0.2
            if self.custom_acc_profile[self._get_time_slice_T_array(t)] > 0:
                color = 'b'
                ls = '-'
                lw=0.2

            if ID == 0:
                lw=1
                ls = '-'
                label = 'start, t=%2.2e (s)'%t
                color = 'black'
            if ID == t_array.size - 1:
                lw=1
                ls = '-'
                label = 'stop, t=%2.2e (s)'%t

            p.add_model_plot(model=s, label=label,line_style=ls,color=color, update=False,lw=lw,auto_label=False)


        if sed_data is not None:
             p.add_data_plot(sed_data)

        p.update_plot()
        return p

    def show_model(self, getstring=False, names_list=None, sort_key=None):
        print('-'*80)
        print("JetTimeEvol model description")
        print('-'*80)
        self._build_tempev_table(self.jet_rad, self._jet_acc)
        print(" ")
        print("physical setup: ")
        print("")
        print('-'*80)
        _show_table(self._tempev_table)
        print("")
        print("model parameters: ")
        print("")
        print('-'*80)
        self.show_pars()

    def _build_row_dict(self, name, type='', unit='', val='', val_by=None, islog=False, unit1=''):
        row_dict = {}
        row_dict['name'] = name
        row_dict['par type'] = type
        row_dict['units'] = unit
        row_dict['val'] = val
        if val_by is not None:
            val_by = val / val_by
        row_dict['val*'] = val_by
        row_dict['units*'] = unit1
        row_dict['log'] = islog
        return row_dict

    def _build_tempev_table(self, jet_rad,jet_acc):

        _names = ['name', 'par type', 'val', 'units', 'val*', 'units*', 'log', ]

        rows = []
        rows.append(self._build_row_dict('delta t', 'time', 's', val=self.delta_t, val_by=self.t_unit_rad,
                                         unit1='R/c', islog=False))
        rows.append(self._build_row_dict('log. sampling', 'time', '', val=self.log_sampling, islog=False))
        rows.append(
            self._build_row_dict('R/c', 'time', 's', val=self.t_unit_rad, val_by=self.t_unit_rad, unit1='R/c',
                                 islog=False))
        rows.append(self._build_row_dict('Diff coeff', '', 's-1', val=self._temp_ev.Diff_Coeff, islog=False))
        rows.append(self._build_row_dict('Acc coeff', '', 's-1', val=self._temp_ev.Acc_Coeff, islog=False))

        rows.append(self._build_row_dict('IC cooling', '', '', val=self.IC_cooling, islog=False))
        rows.append(self._build_row_dict('Sync cooling', '', '', val=self.Sync_cooling, islog=False))
        rows.append(self._build_row_dict('Diff index', '', '', val=self._temp_ev.Diff_Index, islog=False))
        rows.append(self._build_row_dict('Acc index', '', 's-1', val=self._temp_ev.Acc_Index, islog=False))

        if self._jet_acc is not None:
            rows.append(
                self._build_row_dict('Tesc acc', 'time', 's', val=self._temp_ev.T_esc_Coeff_acc, val_by=self.t_unit_acc,
                                     unit1='R_acc/c', islog=False))

        rows.append(
            self._build_row_dict('Tesc rad', 'time', 's', val=self._temp_ev.T_esc_Coeff_rad, val_by=self.t_unit_rad,
                                 unit1='R/c', islog=False))

        rows.append(
            self._build_row_dict('Eacc max', 'energy', 'erg', val=self._temp_ev.E_acc_max, islog=False))

        #if self.jet_acc is not None:
        rows.append(
            self._build_row_dict('R acc', 'accelerator_size', 'cm', val=self.parameters.R_acc.val))

        #if self.jet_acc is not None:
        rows.append(
            self._build_row_dict('B acc', 'magnetic field', 'cm', val=self.parameters.B_acc.val))

        rows.append(
            self._build_row_dict('T_A0=1/ACC_COEFF', 'time', 's', val=self._temp_ev.t_A0, val_by=self.t_unit_rad,
                                 unit1='R/c', islog=False))
        rows.append(
            self._build_row_dict('T_D0=1/DIFF_COEFF', 'time', 's', val=self._temp_ev.t_D0, val_by=self.t_unit_rad,
                                 unit1='R/c', islog=False))
        rows.append(self._build_row_dict('T_DA0=1/(2*DIFF_COEFF)', 'time', 's', val=self._temp_ev.t_DA0,
                                         val_by=self.t_unit_rad, unit1='R/c', islog=False))

        rows.append(self._build_row_dict('gamma Lambda Turb.  max', '', '', val=self._temp_ev.Gamma_Max_Turb_L_max,
                                         islog=False))
        rows.append(self._build_row_dict('gamma Lambda Coher. max', '', '', val=self._temp_ev.Gamma_Max_Turb_L_coher,
                                         islog=False))

        rows.append(self._build_row_dict('gamma eq Syst. Acc (synch. cool)', '', '', val=self._temp_ev.gamma_eq_t_A,
                                         islog=False))
        rows.append(self._build_row_dict('gamma eq Diff. Acc (synch. cool)', '', '', val=self._temp_ev.gamma_eq_t_D,
                                         islog=False))

        t = BlazarSED.Sync_tcool(jet_acc._blob, self._temp_ev.gamma_eq_t_D)
        rows.append(self._build_row_dict('T cooling(gamma_eq=gamma_eq_Diff)', '', 's', val=t, islog=False))
        t = BlazarSED.Sync_tcool(jet_acc._blob, self._temp_ev.gamma_eq_t_A)
        rows.append(self._build_row_dict('T cooling(gamma_eq=gamma_eq_Sys)', '', 's', val=t, islog=False))
        t = BlazarSED.Sync_tcool(jet_acc._blob, self._temp_ev.gamma_eq_t_A)
        rows.append(
            self._build_row_dict('T min. synch. cooling', '', 's', val=self.t_Sync_cool_pre_run.min(), islog=False))

        if self.Q_inj is not None:
            rows.append(self._build_row_dict('L inj (electrons)', 'injected lum.', 'erg/s', val=self.eval_L_tot_inj(),
                                             islog=False))
            #rows.append(self._build_row_dict('E_inj (electrons)', '', 'erg', val=self.eval_E_tot_inj(), islog=False))

        self._tempev_table = Table(rows=rows, names=_names, masked=False)

        self._fromat_column_entry(self._tempev_table)

    def _fromat_column_entry(self, t):

        for n in t.colnames:

            for ID, v in enumerate(t[n].data):
                try:
                    c = ast.literal_eval(t[n].data[ID])
                    if type(c) == int:
                        t[n].data[ID] = '%d' % c
                    else:
                        t[n].data[ID] = '%e' % c
                except:
                    pass

    def _build_par_dict(self):
        """
        These are the model parameters to set after object creation:
        eg:
            temp_ev_acc.parameters.duration.val=1E4

        model parameters
        ----------------
        duration: float (s)
            duration of the evolution in seconds

        gmin_grid: float
            lower bound of the gamma grid for the temporal evolution

        gmax_grid: float
            upper bound of the gamma grid for the temporal evolution

        gamma_grid_size: int
            size of the gamma grid

        TStart_Acc: float (s)
            starting time of the acceleration process

        TStop_Acc: float (s)
            stop time of the acceleration process

        TStart_Inj: float (s)
            starting time of the injection process

        TStop_Inj: float (s)
            stop time of the injection process

        T_esc: float (R/c)
            escape time scale in  (R/c)

        Esc_Index: float
            power-law index for the escapce term t_esc(gamma)=T_esc*gamma^(Esc_Index)

        t_D0: float (s)
            acceleration time scale for diffusive acceleration term

        t_A0: float (s)
            acceleration time scale for the systematic acceleration term

        Diff_Index: float (s)
            power-law index for the diffusive acceleration term

        Acc_Index: float (s)
            power-law index for the systematic acceleration term

        Lambda_max_Turb: float (cm)
            max scale of the turbulence

        Lambda_choer_Turb_factor: float (cm)
           max scale   for the quasi-linear resonant regime

        t_size: int
            number of steps for the time grid

        num_samples: int
            number of the time steps saved in the output

        log_sampling: bool
           if True, the time grid is logarithmically spaced

        L_inj: float (erg/s)
            if not None, the inj function is rescaled to match L_inj
        """

        model_dict_temp_ev = {}
        model_dict_jet_acc = {}

        model_dict_temp_ev['duration'] = JetModelDictionaryPar(ptype='time_grid', vmin=0, vmax=None, punit='s', froz=True, log=False,val=1E5)

        model_dict_temp_ev['gmin_grid'] = JetModelDictionaryPar(ptype='gamma_grid', vmin=0, vmax=None, punit='', froz=True, log=False, val=1E1,jetkernel_par_name='gmin_griglia')

        model_dict_temp_ev['gmax_grid'] = JetModelDictionaryPar(ptype='gamma_grid', vmin=0, vmax=None, punit='', froz=True, log=False, val=1E8,jetkernel_par_name='gmax_griglia')

        model_dict_temp_ev['gamma_grid_size'] = JetModelDictionaryPar(ptype='gamma_grid', vmin=0, vmax=None, punit='', froz=True, log=False, val=5000,jetkernel_par_name='gamma_grid_size')

        model_dict_temp_ev['TStart_Acc'] = JetModelDictionaryPar(ptype='time_grid', vmin=0, vmax=None, punit='s', froz=True,
                                                         log=False,val=0)

        model_dict_temp_ev['TStop_Acc'] = JetModelDictionaryPar(ptype='time_grid', vmin=0, vmax=None, punit='s', froz=True,
                                                         log=False,val=1E5)

        model_dict_temp_ev['TStart_Inj'] = JetModelDictionaryPar(ptype='time_grid', vmin=0, vmax=None, punit='s', froz=True,
                                                         log=False,val=0)

        model_dict_temp_ev['TStop_Inj'] = JetModelDictionaryPar(ptype='time_grid', vmin=0, vmax=None, punit='s', froz=True,
                                                         log=False,val=1E5)

        model_dict_temp_ev['T_esc_acc'] = JetModelDictionaryPar(ptype='escape_time', vmin=None, vmax=None, punit='(R_acc/c)', froz=True,
                                                         log=False,val=2.0,jetkernel_par_name='T_esc_Coeff_R_by_c_acc')

        model_dict_temp_ev['T_esc_rad'] = JetModelDictionaryPar(ptype='escape_time', vmin=None, vmax=None, punit='(R/c)', froz=True,
                                                   log=False, val=2.0, jetkernel_par_name='T_esc_Coeff_R_by_c_rad')

        model_dict_temp_ev['Esc_Index'] = JetModelDictionaryPar(ptype='fp_coeff_index', vmin=None, vmax=None, punit='', froz=True,
                                                            log=False,val=0.0)

        model_dict_temp_ev['t_D0'] = JetModelDictionaryPar(ptype='acceleration_time', vmin=0, vmax=None, punit='s', froz=True,
                                                            log=False,val=1E4)

        model_dict_temp_ev['t_A0'] = JetModelDictionaryPar(ptype='acceleration_time', vmin=0, vmax=None, punit='s', froz=True,
                                                            log=False,val=1E3)

        model_dict_temp_ev['Diff_Index'] = JetModelDictionaryPar(ptype='fp_coeff_index', vmin=0, vmax=None, punit='s', froz=True,
                                                     log=False,val=2)

        model_dict_temp_ev['Acc_Index'] = JetModelDictionaryPar(ptype='fp_coeff_index', vmin=None, vmax=None, punit='', froz=True,
                                                     log=False,val=1)

        model_dict_jet_acc['R_acc'] = JetModelDictionaryPar(ptype='accelerator_size', vmin=0, vmax=None, punit='cm',
                                                            jetkernel_par_name='R',
                                                            froz=True,
                                                            log=False, val=1E15)

        model_dict_jet_acc['B_acc'] = JetModelDictionaryPar(ptype='magnetic_field', vmin=0, vmax=None, punit='G',
                                                            jetkernel_par_name='B',
                                                            froz=True,
                                                            log=False, val=0.1)

        model_dict_temp_ev['E_acc_max'] = JetModelDictionaryPar(ptype='acc_energy', vmin=0, vmax=None, punit='erg',
                                                       froz=True,
                                                       log=False, val=1E60)

        model_dict_temp_ev['Lambda_max_Turb'] = JetModelDictionaryPar(ptype='turbulence_scale', vmin=0, vmax=None, punit='cm', froz=True,
                                                          log=False,val=1E15)

        model_dict_temp_ev['Lambda_choer_Turb_factor'] = JetModelDictionaryPar(ptype='turbulence_scale', vmin=0, vmax=None, punit='cm',
                                                                froz=True,log=False, val=0.1)

        model_dict_temp_ev['t_size'] = JetModelDictionaryPar(ptype='time_grid', vmin=0, vmax=None,
                                                                         punit='',
                                                                         froz=True,
                                                                         log=False,val=1000,
                                                                        jetkernel_par_name='T_SIZE')

        model_dict_temp_ev['num_samples'] = JetModelDictionaryPar(ptype='time_ev_output', vmin=0, vmax=None, punit='', froz=True, log=False, val=50,jetkernel_par_name='NUM_SET')

        #model_dic['log_sampling'] = JetModelDictionaryPar(ptype='time_ev_output', vmin=0, vmax=None, punit='', froz=True, log=False, val=0,allowed_values=[0,1],jetkernel_par_name='LOG_SET')

        #model_dic['IC_cooling'] = JetModelDictionaryPar(ptype='time_ev_output', vmin=0, vmax=None, punit='', froz=True, log=False, val=0,allowed_values=[0,1],jetkernel_par_name='do_Compton_cooling')

        model_dict_temp_ev['L_inj'] = JetModelDictionaryPar(ptype='inj_luminosity', vmin=0, vmax=None,
                                                        punit='erg/s',
                                                        froz=True,
                                                        log=False,
                                                        val=1E39)

        return model_dict_temp_ev, model_dict_jet_acc
