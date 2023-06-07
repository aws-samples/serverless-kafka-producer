package aws.samples.kafka.lambdaconsumer;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;

import software.amazon.lambda.powertools.logging.Logging;
/**
 * Lambda function entry point. You can change to use other pojo type or implement
 * a different RequestHandler.
 *
 * @see <a href=https://docs.aws.amazon.com/lambda/latest/dg/java-handler.html>Lambda Java Handler</a> for more information
 */
public class App implements RequestHandler<Object, Object> {

    Logger log = LogManager.getLogger();

   



    @Override
    @Logging (logEvent = true)
    public Object handleRequest(final Object input, final Context context) {
        
        log.info("Received message!");

        return true;
    }
}
