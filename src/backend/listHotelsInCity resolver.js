import { util } from '@aws-appsync/utils';

export function request(ctx) {
    const id = ctx.args.id
    const bucket = "travel-sample"
    const scope = "inventory"
    const collection = "hotel"
    const username = ctx.arguments.auth.cb_username
    const password = ctx.arguments.auth.cb_password
    const token = util.base64Encode(`${username}:${password}`)
    const auth = `Basic ${token}`
    var sql_query = `SELECT c.* FROM ${collection} AS c WHERE city = "${ctx.arguments.city}"`

    // Log to CloudWatch for debugging (best practice)
    console.log("Request Context:", ctx)
    
    const requestObject = {
        method: 'POST',
        resourcePath: `/_p/query/query/service`,
        params: {
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': auth
            },
            body: {
                query_context: `default:${bucket}.${scope}`,
                statement: sql_query,
                timeout: "30m"
            }
        }
    }
    
    // Log the outgoing request
    console.log("Outgoing Request to Data API:", requestObject)
    
    return requestObject;
}

export function response(ctx) {
    // Log the complete response context
    console.log("Response Context:", ctx)
        
    // Parse the response body if it's a string
    let parsedResult = ctx.result.body;
    if (typeof ctx.result.body === 'string') {
        parsedResult = JSON.parse(ctx.result.body);
        console.log("Parsed Result:", parsedResult)
    }
    
    // GraphQL will automatically filter this based on your query selection set
    return parsedResult.results
}