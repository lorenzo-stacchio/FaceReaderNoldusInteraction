  File "C:\Users\Chiqu\.conda\envs\social_scraper\lib\threading.py", line 1016, in _bootstrap_inner
     self.run()
   File "C:\Users\Chiqu\.conda\envs\social_scraper\lib\threading.py", line 953, in run
     self._target(*self._args, **self._kwargs)
   File "C:\Users\Chiqu\Documents\GitHub\FaceReaderNoldusInteraction\FaceReaderConnector.py", line 227, in start_session
     self.push_to_server(csv_path, time_stamp_check_offset, timestamp_loop)
   File "C:\Users\Chiqu\Documents\GitHub\FaceReaderNoldusInteraction\FaceReaderConnector.py", line 167, in push_to_server
     max_idx = emotion_df['Value'].astype(float).idxmax()
   File "C:\Users\Chiqu\.conda\envs\social_scraper\lib\site-packages\pandas\core\series.py", line 2761, in idxmax
     i = self.argmax(axis, skipna, *args, **kwargs)
   File "C:\Users\Chiqu\.conda\envs\social_scraper\lib\site-packages\pandas\core\base.py", line 751, in argmax
     result = nanops.nanargmax(delegate, skipna=skipna)
   File "C:\Users\Chiqu\.conda\envs\social_scraper\lib\site-packages\pandas\core\nanops.py", line 1148, in nanargmax
     result = values.argmax(axis)
 ValueError: attempt to get argmax of an empty sequence