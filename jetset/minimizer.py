

"""
===================================================================
Module: minimizer
===================================================================

This module contains all the classes necessary to estimate the phenomenlogical
characterization of the SED, such as spectral indices, peack frequenicies
and fluxes




Classes and Inheritance Structure
-------------------------------------------------------------------

.. inheritance-diagram:: BlazarSEDFit.minimizer
   


Classes relations
----------------------------------------------

.. figure::  classes_minimizer.png
   :align:   center     


  

.. autosummary::
    

   fit_SED
   eval_SED
   residuals_SED
   
    
Module API
-------------------------------------------------------------------

"""

from __future__ import absolute_import, division, print_function

from builtins import (bytes, str, open, super, range,
                      zip, round, input, int, pow, object, map, zip)

__author__ = "Andrea Tramacere"


import scipy as s

import numpy as np

#import os

import sys

from scipy.stats import chi2

import iminuit
from iminuit.frontends import ConsoleFrontend

from scipy.optimize import leastsq

from scipy.optimize import least_squares,curve_fit

from leastsqbound.leastsqbound import  leastsqbound


from .output import section_separator,WorkPlace,makedir




__all__=['fit_results','fit_SED','residuals_Fit','Minimizer']

class fit_results(object):
    """
    Class to store the fit results 
    
    Parameters
     
    
    Members
    :ivar fit_par: fit_par
    :ivar info: info
    :ivar mesg: mesg
    :ivar success: success
    :ivar chisq: chisq
    :ivar dof: dof
    :ivar chisq_red: chisq_red
    :ivar null_hyp_sig: null_hyp_sig
    :ivar fit_report: ivar get_report()
    -------
    
    """
    
    def __init__(self,name,parameters,calls,mesg,success,chisq,dof,chisq_red,null_hyp_sig,wd):

        self.name=name
        self.parameters=parameters
        self.calls=calls
        self.mesg=mesg
        self.success=success
        self.chisq=chisq
        self.dof=dof
        self.chisq_red=chisq_red
        self.null_hyp_sig=null_hyp_sig
        self.fit_report=self.get_report()
        self.wd=wd
         

    def get_report(self):
        out=[]
        out.append("")        
        out.append("**************************************************************************************************")
        out.append("Fit report")
        out.append("")
        out.append("Model: %s"%self.name)
        pars_rep=self.parameters.show_pars(getstring=True)
        for string in pars_rep:
            out.append(string)
        
        out.append("")
        out.append("converged=%s"%self.success)
        out.append("calls=%d"%self.calls)
        out.append("mesg=%s"%self.mesg)
        out.append("dof=%d"%self.dof)
        out.append("chisq=%f, chisq/red=%f null hypothesis sig=%f"%(self.chisq,self.chisq_red,self.null_hyp_sig))
        out.append("")
        out.append("best fit pars")
        
        pars_rep=self.parameters.show_best_fit_pars(getstring=True)
        for string in pars_rep:
            out.append(string)
            
        #for pi in range(len(self.fit_par)):
            #print pi,covar
        #    out.append("par %2.2d, %16s"%(pi,self.fit_par[pi].get_bestfit_description()))  
        #out.append("-----------------------------------------------------------------------------------------")
        out.append("**************************************************************************************************")    
        out.append("")
        return out
        
    
    def show_report(self):
        for text in self.fit_report:
        
            print (text)
    
    def save_report(self,wd=None,name=None):
        if wd is None:
            wd=self.wd
        
        if name is None:
            name='report_%s'%self.name+'.txt'
        
            
        outname='%s/%s'%(wd,name)
         
        outfile=open(outname,'w')
    
        
        for text in self.fit_report:
        
            print>>outfile,text
            
        outfile.close()
        
class Minimizer(object):
    def __init__(self):
        pass


    def set_minimizer(self):
        pass

    def fit(self):
        return


def fit_SED(fit_Model,SEDdata,nu_fit_start,nu_fit_stop,fitname=None,fit_workplace=None,loglog=False,silent=False,get_conf_int=False,max_ev=0,use_facke_err=False,minimizer='leastsqbound'):
    __accepted__=['leastsqbound','minuit','least_squares']

    if minimizer not in __accepted__:
        raise RuntimeError ('minimizer ',minimizer, 'not accepted, please choose among',__accepted__)

    """
    function to run the minimization
    
    Parameters
     

    :param SEDModel: :class:`BlazarSEDFit.model.SEDmodel` object
    :param SEDdata:  :class:`BlazarSEDFit.data_loader.ObsData` object
    :param nu_fit_start: (float) minimum value of the frequency fit range in Hz (logarithmic scale)
    :param nu_fit_stop: (float) maximum value of the frequency fit range in Hz (logarithmic scale)
    :param fitname: (str), optional, name for the fit
    :param workplace:
    :param components:
    :param template:
    :param template_func:
    :param template_scale:
    :param build_SEDModel:
    
    
    """
    
    if fitname is None:
        fitname= fit_Model.name +'_' + WorkPlace.flag
        
    
    cnt=[0] 
    res_check=[0]
    
    if fit_workplace is None:
        fit_workplace=WorkPlace()
        out_dir= fit_workplace.out_dir + '/' + fitname + '/'
    else:
        out_dir=fit_workplace.out_dir+'/'+fitname+'/'

    makedir(out_dir)    

    for model in fit_Model.components:
        if model.model_type=='jet':
            model.set_path(out_dir)
           
    
    if SEDdata.data['dnuFnu_data'] is None:
        SEDdata.data['dnuFnu_data']=s.ones(SEDdata.data['nu_data'].size)
    

    
    
    #filter data points
    msk1= SEDdata.data['nu_data']>nu_fit_start
    msk2= SEDdata.data['nu_data']<nu_fit_stop
    msk_zero_error=SEDdata.data['dnuFnu_data']>0.0
    #msk = s.array([(el>nu_fit_start) and (el<nu_fit_stop) for el in SEDdata.data['nu_data']])
    #print msk1.size,msk2.size,SEDdata.data['UL'].size
    msk=msk1*msk2*np.invert(SEDdata.data['UL'])*msk_zero_error
   
    
    if loglog==False:
        nu_fit=SEDdata.data['nu_data'][msk]
        nuFnu_fit=SEDdata.data['nuFnu_data'][msk]
        if use_facke_err==False:
            err_nuFnu_fit=SEDdata.data['dnuFnu_data'][msk]
        else:
            err_nuFnu_fit=SEDdata.data['dnuFnu_facke'][msk]
    else:
        nu_fit=SEDdata.data['nu_data_log'][msk]
        nuFnu_fit=SEDdata.data['nuFnu_data_log'][msk]
        err_nuFnu_fit=SEDdata.data['dnuFnu_data_log'][msk]
        if use_facke_err==False:
            err_nuFnu_fit=SEDdata.data['dnuFnu_data_log'][msk]
        else:
            err_nuFnu_fit=SEDdata.data['dnuFnu_facke_log'][msk]
    
    if silent==False:
        print ("filtering data in fit range = [%e,%e]"%(nu_fit_start,nu_fit_stop))
        print ("data length",nu_fit.size)

    #print nu_fit,len(nu_fit)


    
    
    
    #set starting value of parameters
    for par in fit_Model.parameters.par_array:
        if get_conf_int==True:
            par.set_fit_initial_value(par.best_fit_val)
        else:
            par.set_fit_initial_value(par.val)
    
    fit_par_free=[par for par in fit_Model.parameters.par_array if par.frozen==False]

    pinit=[par.get_fit_initial_value() for par in fit_par_free]
    




    # bounds
    free_pars=0
     
    for pi in range(len(fit_Model.parameters.par_array)):

        if fit_Model.parameters.par_array[pi].frozen==False:
            free_pars+=1
   
   
        
    if silent==False:
        print  (section_separator)
        print ("*** start fit process ***")
        print ("initial pars: ")
        
        fit_Model.parameters.show_pars()
    
        
    if minimizer=='leastsqbound':
        bounds = [(par.fit_range_min, par.fit_range_max) for par in fit_par_free]

        #for par in fit_par_free:
        #    print(par.name, par.fit_range_min, par.fit_range_max)

        pout,covar,info,mesg,success = leastsqbound(residuals_Fit,
                                                   pinit,
                                                   args=(fit_par_free,nu_fit,nuFnu_fit,err_nuFnu_fit,fit_Model,loglog,cnt,res_check),
                                                   xtol=5.0E-8,
                                                   ftol=5.0E-8,
                                                   full_output=1,
                                                   bounds=bounds,
                                                   maxfev=1000)

        chisq = sum(info["fvec"] * info["fvec"])
        dof = len(nu_fit) - free_pars
        chisq_red = chisq / float(dof)
        null_hyp_sig = 1.0 - chi2.cdf(chisq, dof)
        calls=info['nfev']
    elif minimizer=='least_squares':



        bounds= ([-np.inf if par.fit_range_min is None else par.fit_range_min for par in fit_par_free],
                      [np.inf if par.fit_range_max is None else par.fit_range_max for par in fit_par_free])

        #for par in fit_par_free:
        #    print(par.name, par.fit_range_min, par.fit_range_max)

        fit=least_squares(residuals_Fit,
                      pinit,
                      args=(fit_par_free, nu_fit, nuFnu_fit, err_nuFnu_fit, fit_Model, loglog,
                            cnt,
                            res_check),
                      xtol=1.0E-8,
                      ftol=1.0E-8,
                      jac='3-point',
                      loss='cauchy',
                      f_scale=0.01,
                      bounds=bounds,
                      max_nfev=None,
                      verbose=2)
        #else:

        pout=fit.x
        calls=fit.nfev
        mesg=fit.message
        success=fit.success
        status=fit.status
        J=fit.jac
        covar = np.linalg.inv(2 * np.dot(J.T, J))

        chisq = sum(fit.fun * fit.fun)
        dof = len(nu_fit) - free_pars
        chisq_red = chisq / float(dof)
        null_hyp_sig = 1.0 - chi2.cdf(chisq, dof)
        print('c->',status,calls,mesg)
        #chol_cov = np.linalg.cholesky(covar).T

    elif minimizer=='minuit':
        bounds = [(par.fit_range_min, par.fit_range_max) for par in fit_par_free]
        mm=MinutiMinimizer(pinit,bounds,fit_par_free,nu_fit,nuFnu_fit,err_nuFnu_fit,fit_Model,loglog,cnt,res_check)
        mm.minuit_fun.tol=1.0
        mm.minuit_fun.set_strategy(0)
        mm.minuit_fun.migrad()


        dof = len(nu_fit) - free_pars
        chisq=mm.get_chisq()
        chisq_red = chisq / float(dof)
        null_hyp_sig = 1.0 - chi2.cdf(chisq, dof)
        errors=mm.minuit_fun.errors
        mesg=''
        calls=cnt[0]
        success=True
        status=1
        values=mm.minuit_fun.values
        pout = [values[k] for k in values.keys()]
        #print('c->', status, calls, mesg)

        #curve_fit()
    #    pout,covar,info,mesg,success = leastsq(residuals_Fit, pinit,args=(fit_par_free,nu_fit,nuFnu_fit,err_nuFnu_fit,fit_Model,loglog,cnt,res_check),xtol=5.0E-8,ftol=5.0E-8,full_output=1,maxfev=max_ev)
    #sys.stdout.flush()
    #
    print ("res check",res_check[0].sum(),(res_check[0]*res_check[0]).sum()  )


    
    if get_conf_int==True:
        return chisq
    

    if minimizer!='minuit':
        if covar is None:
            print ("!Warning, no covariance matrix produced")
            par_err=s.zeros(len(pout))
        else:
            par_err=[s.sqrt(s.fabs(covar[pi,pi])*chisq_red)  for pi in range(len(fit_par_free))]
    else:
        par_err=[errors[k] for k in errors.keys()]




    
    for pi in range(len(fit_par_free)):
        fit_par_free[pi].set(val=pout[pi])
        fit_par_free[pi].best_fit_val=pout[pi]
        fit_par_free[pi].best_fit_err=par_err[pi]    
        
            
    
            
            
    best_fit=fit_results(fitname,fit_Model.parameters,calls,mesg,success,chisq,dof,chisq_red,null_hyp_sig,out_dir)
   
    if silent==False:
        best_fit.show_report()
   

    fit_Model.set_nu_grid(nu_min=nu_fit_start,nu_max=nu_fit_stop)
    fit_Model.eval(fill_SED=True,loglog=loglog,phys_output=True)
    

   
    res_bestfit=residuals_Fit(pout,fit_par_free,nu_fit,nuFnu_fit,err_nuFnu_fit,fit_Model,loglog)

    if loglog==True:
        fit_Model.SED.fill(nu_residuals=np.power(10,nu_fit),residuals=res_bestfit)
    else:
        fit_Model.SED.fill(nu_residuals=nu_fit,residuals=res_bestfit)     
    
    if silent==False:
        print  (section_separator)
     
    return best_fit


class MinutiMinimizer(object):

    def __init__(self,pinit,bounds, fit_par, nu_data, nuFnu_data, err_nuFnu_data, best_fit_SEDModel, loglog,cnt,res_check):

        self.fit_par = fit_par
        self.nu_data = nu_data
        self.nuFnu_data = nuFnu_data
        self.err_nuFnu_data = err_nuFnu_data
        self.best_fit_SEDModel = best_fit_SEDModel
        self.loglog=loglog
        self.cnt=cnt
        self.res_check=res_check

        self._set_minuit_func(pinit, bounds)

    def _set_minuit_func(self, p_init, bounds):
        p_names = ['par_{}'.format(_) for _ in range(len(p_init))]
        p_bound_names = ['limit_par_{}'.format(_) for _ in range(len(p_init))]
        kwdarg = {}
        for n, p, bn, b in zip(p_names, p_init, p_bound_names, bounds):
            kwdarg[n] = p
            kwdarg[bn] = b

        print('dict', kwdarg)

        self.minuit_fun = iminuit.Minuit(
            fcn=self.minimize_me,
            forced_parameters=p_names,
            **kwdarg,
            frontend=ConsoleFrontend())

    def minimize_me(self, *p):
        self.p = p
        res=residuals_Fit(p,
                          self.fit_par,
                          self.nu_data,
                          self.nuFnu_data,
                          self.err_nuFnu_data,
                          self.best_fit_SEDModel,
                          self.loglog,
                          cnt=self.cnt,
                          res_check=self.res_check)

        return np.sum(res*res)

    def get_chisq(self):
        print ('p',self.p)
        return self.minimize_me(*self.p)

def residuals_Fit(p,fit_par,nu_data,nuFnu_data,err_nuFnu_data,best_fit_SEDModel,loglog,cnt=None,res_check=None):
    

    for pi in range(len(fit_par)):
        fit_par[pi].set(val=p[pi])


    model=best_fit_SEDModel.eval(nu=nu_data,fill_SED=False,get_model=True,loglog=loglog)
    

   
    res = (nuFnu_data-model)/(err_nuFnu_data)
    
    if res_check is not None:
        res_check[0]=res
    

    if cnt is not None:
        cnt[0]=cnt[0]+1
        if np.mod(cnt[0],10)==0 and cnt[0]!=0:
            print("\rminim function calls=%d, res=%f, chisq=%f "%(cnt[0],res.sum(),(res_check[0]*res_check[0]).sum()), end="")
            #sys.stdout.write("minim function calls=%d, res=%f, chisq=%f "%(cnt[0],res.sum(),(res_check[0]*res_check[0]).sum()))
            sys.stdout.flush()
            for x in range(120):
                sys.stdout.write('\b')

    return res







