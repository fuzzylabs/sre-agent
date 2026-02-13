import { createLogger, format, transports, Logger } from 'winston';

// Define log levels
const levels = {
  error: 0,
  warn: 1,
  info: 2,
  debug: 3,
};

// Define log colors
const colors = {
  error: 'red',
  warn: 'yellow',
  info: 'green',
  debug: 'blue',
};

// Create the logger
const logger: Logger = createLogger({
  levels,
  format: format.combine(
    format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    format.errors({ stack: true }),
    format.splat(),
    format.json()
  ),
  defaultMeta: { service: 'kubernetes-server' },
  transports: [
    // Console transport
    new transports.Console({
      format: format.combine(
        format.colorize({ colors }),
        format.printf(
          (info: any) => {
            const { level, message, timestamp, ...meta } = info;
            return `${timestamp} [${level}]: ${message} ${Object.keys(meta).length ? JSON.stringify(meta, null, 2) : ''}`;
          }
        )
      ),
    }),
  ],
});

export default logger; 
