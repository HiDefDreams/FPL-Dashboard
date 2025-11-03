import streamlit as st
import pandas as pd
import os
import glob

def clear_cache():
    """Clear all cache files"""
    cache_files = glob.glob("fpl_cache/*.json")
    for f in cache_files:
        try:
            os.remove(f)
        except:
            pass

def get_cache_info():
    """Get information about cached data"""
    cache_size = 0
    if os.path.exists("fpl_cache"):
        cache_files = os.listdir("fpl_cache")
        cache_size = len([f for f in cache_files if f.endswith('.json')])
    return cache_size