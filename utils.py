    import streamlit as st
    import logging
    
    def init_session_state():
        """Inicializa las variables necesarias en el st.session_state."""
        if 'paradas_df' not in st.session_state:
            st.session_state.paradas_df = None
        if 'vehiculos_df' not in st.session_state:
            st.session_state.vehiculos_df = None
        if 'resultados' not in st.session_state:
            st.session_state.resultados = None
        if 'logs' not in st.session_state:
            st.session_state.logs = []
    
    def get_logger():
        """Configura y devuelve un logger que escribe en st.session_state."""
        logger = logging.getLogger("Rout2App")
        
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            class StreamlitLogHandler(logging.Handler):
                def emit(self, record):
                    log_entry = self.format(record)
                    # Prepend to show newest first
                    st.session_state.logs.insert(0, log_entry)
    
            handler = StreamlitLogHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def display_logs():
        """Muestra los logs acumulados en un expander en la UI."""
        with st.expander("📋 Ver Logs de la Sesión"):
            if st.session_state.logs:
                log_text = "\n".join(st.session_state.logs)
                st.code(log_text, language="log")
            else:
                st.write("No hay logs para esta sesión todavía.")
    
